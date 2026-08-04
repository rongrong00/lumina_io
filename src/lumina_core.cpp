// lumina_core: fast parallel HDF5 dataset reader for LUMINA simulation output.
//
// Strategy: HDF5 metadata operations (open, dtype, chunk addresses) happen
// under a global mutex since the HDF5 library is not thread-safe. For the
// common case in LUMINA output -- chunked, *uncompressed*, little-endian
// datasets whose chunks span all trailing dimensions -- the raw bytes of each
// chunk are contiguous in the file, so after resolving chunk addresses we
// bypass libhdf5 and read with many concurrent pread() calls straight into
// the destination numpy buffer. Anything else (filters, exotic chunking,
// big-endian) falls back to a plain H5Dread under the mutex.
//
// read()       -- one row range [start, start+count) along axis 0
// read_multi() -- many row ranges in a single parallel pass (batched halos)
// read_box()   -- an N-d sub-box [start_d, start_d+count_d) per axis; chunks
//                 intersecting the box are pread() whole in parallel and the
//                 overlaps strided-copied out (serves datasets whose chunks
//                 do NOT span the trailing dims, e.g. 128^3 grid/lightcone
//                 chunks, which the row path cannot)

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <hdf5.h>

#include <algorithm>
#include <atomic>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <fcntl.h>
#include <unistd.h>

namespace py = pybind11;

static std::mutex h5_mutex;          // serializes all libhdf5 calls
static int g_num_threads = 0;        // 0 -> auto

static int effective_threads() {
    if (g_num_threads > 0) return g_num_threads;
    const char* env = std::getenv("LUMINA_NTHREADS");
    if (env) {
        int n = std::atoi(env);
        if (n > 0) return n;
    }
    unsigned hw = std::thread::hardware_concurrency();
    return std::max(1u, std::min(hw, 16u));
}

struct H5Closer {
    herr_t (*close)(hid_t);
    hid_t id;
    ~H5Closer() { if (id >= 0) close(id); }
};

// Map an HDF5 file datatype to a numpy dtype string, or "" if unsupported.
static std::string dtype_string(hid_t t) {
    H5T_class_t cls = H5Tget_class(t);
    size_t size = H5Tget_size(t);
    H5T_order_t order = H5Tget_order(t);
    char e = (order == H5T_ORDER_BE) ? '>' : '<';
    if (cls == H5T_FLOAT) {
        if (size == 2 || size == 4 || size == 8)
            return std::string(1, e) + "f" + std::to_string(size);
    } else if (cls == H5T_INTEGER) {
        char k = (H5Tget_sign(t) == H5T_SGN_NONE) ? 'u' : 'i';
        if (size == 1 || size == 2 || size == 4 || size == 8)
            return std::string(1, e) + k + std::to_string(size);
    }
    return "";
}

struct ReadSegment {        // copy plan: file byte range -> dest buffer offset
    uint64_t file_off;
    uint64_t dst_off;
    uint64_t nbytes;
    bool zero_fill;         // unallocated chunk -> fill with zeros
};

struct RowRange { int64_t start, count; };

struct DatasetMeta {
    std::vector<hsize_t> dims;
    std::string dtype;
    std::vector<hsize_t> chunks;   // empty if not chunked
    int nfilters = 0;
    std::string layout;            // "contiguous" | "chunked" | "compact" | "virtual"
    uint64_t row_bytes = 0;
    size_t itemsize = 0;
};

// --- helpers requiring h5_mutex held -----------------------------------------

static hid_t open_quiet(const std::string& path) {
    hid_t f = H5Fopen(path.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);
    if (f < 0) throw std::runtime_error("lumina_core: cannot open file: " + path);
    return f;
}

static DatasetMeta get_meta_locked(hid_t dset) {
    DatasetMeta m;
    hid_t space = H5Dget_space(dset);
    H5Closer sc{H5Sclose, space};
    int rank = H5Sget_simple_extent_ndims(space);
    if (rank < 1) throw std::runtime_error("lumina_core: scalar datasets not supported");
    m.dims.resize(rank);
    H5Sget_simple_extent_dims(space, m.dims.data(), nullptr);

    hid_t ft = H5Dget_type(dset);
    H5Closer tc{H5Tclose, ft};
    m.dtype = dtype_string(ft);

    hid_t dcpl = H5Dget_create_plist(dset);
    H5Closer pc{H5Pclose, dcpl};
    H5D_layout_t lay = H5Pget_layout(dcpl);
    switch (lay) {
        case H5D_CONTIGUOUS: m.layout = "contiguous"; break;
        case H5D_CHUNKED:    m.layout = "chunked"; break;
        case H5D_COMPACT:    m.layout = "compact"; break;
        default:             m.layout = "virtual"; break;
    }
    if (lay == H5D_CHUNKED) {
        m.chunks.resize(rank);
        H5Pget_chunk(dcpl, rank, m.chunks.data());
        m.nfilters = H5Pget_nfilters(dcpl);
    }
    if (!m.dtype.empty()) {
        m.itemsize = (size_t)(m.dtype[2] - '0');
        m.row_bytes = m.itemsize;
        for (size_t i = 1; i < m.dims.size(); ++i) m.row_bytes *= m.dims[i];
    }
    return m;
}

// Build the raw-pread copy plan for a set of row ranges. Returns false if the
// dataset cannot be served by the raw path (filters, BE, partial chunks, ...).
// Chunk addresses are cached, so ranges sharing chunks cost one lookup.
static bool build_plan_locked(hid_t dset, const DatasetMeta& m,
                              const std::vector<RowRange>& ranges,
                              std::vector<ReadSegment>& segs) {
    if (m.dtype.empty() || m.dtype[0] != '<') return false;

    if (m.layout == "contiguous") {
        haddr_t base = H5Dget_offset(dset);
        if (base == HADDR_UNDEF) return false;
        uint64_t dst = 0;
        for (const auto& r : ranges) {
            if (r.count > 0)
                segs.push_back({(uint64_t)base + (uint64_t)r.start * m.row_bytes,
                                dst, (uint64_t)r.count * m.row_bytes, false});
            dst += (uint64_t)r.count * m.row_bytes;
        }
        return true;
    }
    if (m.layout != "chunked" || m.nfilters != 0) return false;
    for (size_t i = 1; i < m.dims.size(); ++i)          // chunks must span trailing dims
        if (m.chunks[i] < m.dims[i]) return false;

    struct ChunkLoc { haddr_t addr; hsize_t size; };
    std::unordered_map<int64_t, ChunkLoc> cache;
    hsize_t crows = m.chunks[0];
    int rank = (int)m.dims.size();
    std::vector<hsize_t> coord(rank, 0);

    uint64_t dst_base = 0;
    for (const auto& r : ranges) {
        if (r.count <= 0) { continue; }
        int64_t c_first = r.start / (int64_t)crows;
        int64_t c_last  = (r.start + r.count - 1) / (int64_t)crows;
        for (int64_t c = c_first; c <= c_last; ++c) {
            auto it = cache.find(c);
            if (it == cache.end()) {
                coord[0] = (hsize_t)c * crows;
                haddr_t addr; hsize_t csize; unsigned fmask;
                if (H5Dget_chunk_info_by_coord(dset, coord.data(), &fmask, &addr, &csize) < 0)
                    return false;
                it = cache.emplace(c, ChunkLoc{addr, csize}).first;
            }
            int64_t c0 = c * (int64_t)crows;
            int64_t r0 = std::max(r.start, c0);
            int64_t r1 = std::min(r.start + r.count, c0 + (int64_t)crows);
            uint64_t nb = (uint64_t)(r1 - r0) * m.row_bytes;
            uint64_t dst = dst_base + (uint64_t)(r0 - r.start) * m.row_bytes;
            if (it->second.addr == HADDR_UNDEF) {       // never written -> fill value (0)
                segs.push_back({0, dst, nb, true});
            } else {
                uint64_t skip = (uint64_t)(r0 - c0) * m.row_bytes;
                if (skip + nb > (uint64_t)it->second.size) return false;
                segs.push_back({(uint64_t)it->second.addr + skip, dst, nb, false});
            }
        }
        dst_base += (uint64_t)r.count * m.row_bytes;
    }
    return true;
}

// Fallback: serialized hyperslab H5Dread with identity (file) type. Call with
// h5_mutex held. dst points at the destination row of the output buffer.
static void h5dread_range_locked(hid_t dset, const DatasetMeta& m,
                                 int64_t start, int64_t count, char* dst) {
    hid_t ft = H5Dget_type(dset);
    H5Closer tc{H5Tclose, ft};
    hid_t fspace = H5Dget_space(dset);
    H5Closer sc{H5Sclose, fspace};
    int rank = (int)m.dims.size();
    std::vector<hsize_t> off(rank, 0), cnt(m.dims.begin(), m.dims.end());
    off[0] = (hsize_t)start; cnt[0] = (hsize_t)count;
    H5Sselect_hyperslab(fspace, H5S_SELECT_SET, off.data(), nullptr, cnt.data(), nullptr);
    hid_t mspace = H5Screate_simple(rank, cnt.data(), nullptr);
    H5Closer mc{H5Sclose, mspace};
    if (H5Dread(dset, ft, mspace, fspace, H5P_DEFAULT, dst) < 0)
        throw std::runtime_error("lumina_core: H5Dread failed");
}

// --- parallel raw I/O --------------------------------------------------------

static void run_segments(const std::string& path, char* dst,
                         std::vector<ReadSegment>& segs, int nthreads) {
    // split very large segments so threads can share them
    const uint64_t MAX_SEG = 64ull << 20;  // 64 MB
    std::vector<ReadSegment> work;
    work.reserve(segs.size());
    for (const auto& s : segs) {
        if (s.zero_fill || s.nbytes <= MAX_SEG) { work.push_back(s); continue; }
        for (uint64_t off = 0; off < s.nbytes; off += MAX_SEG) {
            uint64_t n = std::min(MAX_SEG, s.nbytes - off);
            work.push_back({s.file_off + off, s.dst_off + off, n, false});
        }
    }

    int fd = open(path.c_str(), O_RDONLY);
    if (fd < 0) throw std::runtime_error("lumina_core: cannot open for raw read: " + path);

    std::atomic<size_t> next{0};
    std::atomic<bool> failed{false};
    auto worker = [&]() {
        size_t i;
        while ((i = next.fetch_add(1)) < work.size()) {
            const ReadSegment& s = work[i];
            if (s.zero_fill) { std::memset(dst + s.dst_off, 0, s.nbytes); continue; }
            uint64_t done = 0;
            while (done < s.nbytes) {
                ssize_t r = pread(fd, dst + s.dst_off + done, s.nbytes - done,
                                  (off_t)(s.file_off + done));
                if (r <= 0) { failed.store(true); return; }
                done += (uint64_t)r;
            }
        }
    };

    int nt = std::min<size_t>(std::max(1, nthreads), std::max<size_t>(1, work.size()));
    std::vector<std::thread> threads;
    for (int t = 1; t < nt; ++t) threads.emplace_back(worker);
    worker();
    for (auto& th : threads) th.join();
    close(fd);
    if (failed.load())
        throw std::runtime_error("lumina_core: raw pread failed on " + path);
}

// --- core: read a set of row ranges, concatenated along axis 0 ----------------

static py::array read_ranges(const std::string& path, const std::string& dset_name,
                             std::vector<RowRange> ranges, int nthreads,
                             bool resolve_neg_count) {
    if (nthreads <= 0) nthreads = effective_threads();

    DatasetMeta m;
    std::vector<ReadSegment> segs;
    bool raw_ok = false;
    int64_t total = 0;

    {   // ---- metadata phase, under HDF5 lock, GIL released ----
        py::gil_scoped_release nogil;
        std::lock_guard<std::mutex> lock(h5_mutex);

        hid_t file = open_quiet(path);
        H5Closer fc{H5Fclose, file};
        hid_t dset = H5Dopen2(file, dset_name.c_str(), H5P_DEFAULT);
        if (dset < 0) throw std::runtime_error("lumina_core: no dataset '" + dset_name + "' in " + path);
        H5Closer dc{H5Dclose, dset};

        m = get_meta_locked(dset);
        if (m.dtype.empty())
            throw std::runtime_error("lumina_core: unsupported datatype in " + path + ":" + dset_name);

        int64_t n0 = (int64_t)m.dims[0];
        for (auto& r : ranges) {
            if (r.count < 0 && resolve_neg_count) r.count = n0 - r.start;
            if (r.start < 0 || r.count < 0 || r.start + r.count > n0)
                throw std::runtime_error("lumina_core: row range [" + std::to_string(r.start) +
                                         ", +" + std::to_string(r.count) + ") out of bounds (n=" +
                                         std::to_string(n0) + ")");
            total += r.count;
        }
        raw_ok = build_plan_locked(dset, m, ranges, segs);
        if (!raw_ok) segs.clear();
    }

    // allocate output (needs GIL)
    std::vector<py::ssize_t> shape;
    shape.push_back((py::ssize_t)total);
    for (size_t i = 1; i < m.dims.size(); ++i) shape.push_back((py::ssize_t)m.dims[i]);
    py::array out(py::dtype(m.dtype), shape);
    char* dst = (char*)out.mutable_data();

    {
        py::gil_scoped_release nogil;
        if (raw_ok) {
            run_segments(path, dst, segs, nthreads);
        } else if (total > 0) {
            std::lock_guard<std::mutex> lock(h5_mutex);
            hid_t file = open_quiet(path);
            H5Closer fc{H5Fclose, file};
            hid_t dset = H5Dopen2(file, dset_name.c_str(), H5P_DEFAULT);
            if (dset < 0) throw std::runtime_error("lumina_core: no dataset '" + dset_name + "'");
            H5Closer dc{H5Dclose, dset};
            uint64_t dst_off = 0;
            for (const auto& r : ranges) {
                if (r.count > 0)
                    h5dread_range_locked(dset, m, r.start, r.count, dst + dst_off);
                dst_off += (uint64_t)r.count * m.row_bytes;
            }
        }
    }
    return out;
}

// --- N-dimensional box reads ---------------------------------------------------

struct ChunkJob {                  // one chunk intersecting the requested box
    haddr_t addr;                  // HADDR_UNDEF -> never written, zero fill
    std::vector<int64_t> origin;   // chunk origin in dataset coords
};

// Fallback: serialized hyperslab H5Dread of the whole box. Call with mutex held.
static void h5dread_box_locked(hid_t dset, const std::vector<int64_t>& starts,
                               const std::vector<int64_t>& counts, char* dst) {
    hid_t ft = H5Dget_type(dset);
    H5Closer tc{H5Tclose, ft};
    hid_t fspace = H5Dget_space(dset);
    H5Closer sc{H5Sclose, fspace};
    int rank = (int)starts.size();
    std::vector<hsize_t> off(starts.begin(), starts.end());
    std::vector<hsize_t> cnt(counts.begin(), counts.end());
    H5Sselect_hyperslab(fspace, H5S_SELECT_SET, off.data(), nullptr, cnt.data(), nullptr);
    hid_t mspace = H5Screate_simple(rank, cnt.data(), nullptr);
    H5Closer mc{H5Sclose, mspace};
    if (H5Dread(dset, ft, mspace, fspace, H5P_DEFAULT, dst) < 0)
        throw std::runtime_error("lumina_core: H5Dread (box) failed");
}

// Copy the overlap of one chunk with the box from `src` (the raw chunk, full
// chunk dims) into the output buffer, as contiguous runs. Trailing axes whose
// overlap spans both the full chunk extent and the full output extent are
// fused into longer runs. src == nullptr writes zeros (unallocated chunk).
static void copy_chunk_overlap(const char* src, char* dst,
                               const std::vector<int64_t>& origin,
                               const std::vector<hsize_t>& chunk,
                               const std::vector<int64_t>& starts,
                               const std::vector<int64_t>& counts,
                               const std::vector<hsize_t>& dims, size_t itemsize) {
    const int rank = (int)dims.size();
    std::vector<int64_t> lo(rank), hi(rank);          // overlap, dataset coords
    for (int d = 0; d < rank; ++d) {
        int64_t cext = std::min<int64_t>((int64_t)chunk[d], (int64_t)dims[d] - origin[d]);
        lo[d] = std::max(starts[d], origin[d]);
        hi[d] = std::min(starts[d] + counts[d], origin[d] + cext);
        if (hi[d] <= lo[d]) return;                   // no overlap (shouldn't happen)
    }
    std::vector<int64_t> cstride(rank), ostride(rank);   // in elements
    cstride[rank - 1] = 1; ostride[rank - 1] = 1;
    for (int d = rank - 2; d >= 0; --d) {
        cstride[d] = cstride[d + 1] * (int64_t)chunk[d + 1];   // full (padded) chunk
        ostride[d] = ostride[d + 1] * counts[d + 1];
    }
    // fuse trailing axes that are contiguous in BOTH chunk and output
    int last = rank - 1;
    uint64_t run = itemsize;
    while (true) {
        run *= (uint64_t)(hi[last] - lo[last]);
        if (last > 0 && hi[last] - lo[last] == (int64_t)chunk[last] &&
            hi[last] - lo[last] == counts[last])
            --last;
        else
            break;
    }
    std::vector<int64_t> idx(lo.begin(), lo.begin() + last);   // odometer, dims [0, last)
    while (true) {
        int64_t coff = (lo[last] - origin[last]) * cstride[last];
        int64_t ooff = (lo[last] - starts[last]) * ostride[last];
        for (int d = 0; d < last; ++d) {
            coff += (idx[d] - origin[d]) * cstride[d];
            ooff += (idx[d] - starts[d]) * ostride[d];
        }
        if (src) std::memcpy(dst + (uint64_t)ooff * itemsize,
                             src + (uint64_t)coff * itemsize, run);
        else     std::memset(dst + (uint64_t)ooff * itemsize, 0, run);
        int d = last - 1;
        for (; d >= 0; --d) {
            if (++idx[d] < hi[d]) break;
            idx[d] = lo[d];
        }
        if (d < 0) break;
    }
}

static py::array read_box(const std::string& path, const std::string& dset_name,
                          std::vector<int64_t> starts, std::vector<int64_t> counts,
                          int nthreads) {
    if (nthreads <= 0) nthreads = effective_threads();

    DatasetMeta m;
    std::vector<ChunkJob> jobs;
    uint64_t chunk_bytes = 0;
    bool raw_ok = false;

    {   // ---- metadata phase: bounds, chunk addresses; under HDF5 lock ----
        py::gil_scoped_release nogil;
        std::lock_guard<std::mutex> lock(h5_mutex);

        hid_t file = open_quiet(path);
        H5Closer fc{H5Fclose, file};
        hid_t dset = H5Dopen2(file, dset_name.c_str(), H5P_DEFAULT);
        if (dset < 0) throw std::runtime_error("lumina_core: no dataset '" + dset_name + "' in " + path);
        H5Closer dc{H5Dclose, dset};

        m = get_meta_locked(dset);
        if (m.dtype.empty())
            throw std::runtime_error("lumina_core: unsupported datatype in " + path + ":" + dset_name);
        const int rank = (int)m.dims.size();
        if (starts.size() != counts.size() || (int)starts.size() > rank)
            throw std::runtime_error("lumina_core: read_box starts/counts must have one entry "
                                     "per dataset axis (trailing axes may be omitted)");
        while ((int)starts.size() < rank) {     // omitted trailing axes -> full extent
            starts.push_back(0);
            counts.push_back(-1);
        }
        for (int d = 0; d < rank; ++d) {
            if (counts[d] < 0) counts[d] = (int64_t)m.dims[d] - starts[d];
            if (starts[d] < 0 || counts[d] < 0 || starts[d] + counts[d] > (int64_t)m.dims[d])
                throw std::runtime_error("lumina_core: box out of bounds on axis " + std::to_string(d));
        }

        raw_ok = (m.dtype[0] == '<' && m.layout == "chunked" && m.nfilters == 0);
        int64_t nboxel = 1;
        for (int d = 0; d < rank; ++d) nboxel *= counts[d];
        if (raw_ok && nboxel > 0) {
            chunk_bytes = m.itemsize;
            for (int d = 0; d < rank; ++d) chunk_bytes *= m.chunks[d];
            std::vector<int64_t> c0(rank), c1(rank), ci(rank);   // chunk index ranges
            for (int d = 0; d < rank; ++d) {
                c0[d] = starts[d] / (int64_t)m.chunks[d];
                c1[d] = (starts[d] + counts[d] - 1) / (int64_t)m.chunks[d];
                ci[d] = c0[d];
            }
            std::vector<hsize_t> coord(rank);
            while (true) {                                       // odometer over chunks
                ChunkJob job;
                job.origin.resize(rank);
                for (int d = 0; d < rank; ++d) {
                    job.origin[d] = ci[d] * (int64_t)m.chunks[d];
                    coord[d] = (hsize_t)job.origin[d];
                }
                hsize_t csize; unsigned fmask;
                if (H5Dget_chunk_info_by_coord(dset, coord.data(), &fmask, &job.addr, &csize) < 0) {
                    raw_ok = false;
                    break;
                }
                if (job.addr != HADDR_UNDEF && csize != chunk_bytes) {  // unexpected (filtered?)
                    raw_ok = false;
                    break;
                }
                jobs.push_back(std::move(job));
                int d = rank - 1;
                for (; d >= 0; --d) {
                    if (++ci[d] <= c1[d]) break;
                    ci[d] = c0[d];
                }
                if (d < 0) break;
            }
            if (!raw_ok) jobs.clear();
        }
    }

    std::vector<py::ssize_t> shape(counts.begin(), counts.end());
    py::array out(py::dtype(m.dtype), shape);
    char* dst = (char*)out.mutable_data();
    if (out.size() == 0) return out;

    {
        py::gil_scoped_release nogil;
        if (raw_ok) {
            std::atomic<size_t> next{0};
            std::atomic<bool> failed{false};
            int fd = open(path.c_str(), O_RDONLY);
            if (fd < 0) throw std::runtime_error("lumina_core: cannot open for raw read: " + path);
            auto worker = [&]() {
                std::vector<char> scratch(chunk_bytes);
                size_t i;
                while (!failed.load() && (i = next.fetch_add(1)) < jobs.size()) {
                    const ChunkJob& j = jobs[i];
                    const char* src = nullptr;
                    if (j.addr != HADDR_UNDEF) {
                        uint64_t done = 0;
                        while (done < chunk_bytes) {
                            ssize_t r = pread(fd, scratch.data() + done, chunk_bytes - done,
                                              (off_t)((uint64_t)j.addr + done));
                            if (r <= 0) { failed.store(true); break; }
                            done += (uint64_t)r;
                        }
                        if (failed.load()) return;
                        src = scratch.data();
                    }
                    copy_chunk_overlap(src, dst, j.origin, m.chunks, starts, counts,
                                       m.dims, m.itemsize);
                }
            };
            int nt = (int)std::min<size_t>(std::max(1, nthreads), std::max<size_t>(1, jobs.size()));
            std::vector<std::thread> threads;
            for (int t = 1; t < nt; ++t) threads.emplace_back(worker);
            worker();
            for (auto& th : threads) th.join();
            close(fd);
            if (failed.load())
                throw std::runtime_error("lumina_core: raw pread failed on " + path);
        } else {
            std::lock_guard<std::mutex> lock(h5_mutex);
            hid_t file = open_quiet(path);
            H5Closer fc{H5Fclose, file};
            hid_t dset = H5Dopen2(file, dset_name.c_str(), H5P_DEFAULT);
            if (dset < 0) throw std::runtime_error("lumina_core: no dataset '" + dset_name + "'");
            H5Closer dc{H5Dclose, dset};
            h5dread_box_locked(dset, starts, counts, dst);
        }
    }
    return out;
}

// --- python-facing wrappers ----------------------------------------------------

static py::array read_rows(const std::string& path, const std::string& dset_name,
                           int64_t start, int64_t count, int nthreads) {
    return read_ranges(path, dset_name, {{start, count}}, nthreads, true);
}

static py::array read_multi(const std::string& path, const std::string& dset_name,
                            py::array_t<int64_t> starts, py::array_t<int64_t> counts,
                            int nthreads) {
    auto s = starts.unchecked<1>();
    auto c = counts.unchecked<1>();
    if (s.shape(0) != c.shape(0))
        throw std::runtime_error("lumina_core: starts and counts must have equal length");
    std::vector<RowRange> ranges(s.shape(0));
    for (py::ssize_t i = 0; i < s.shape(0); ++i) ranges[i] = {s(i), c(i)};
    return read_ranges(path, dset_name, std::move(ranges), nthreads, false);
}

// Convert LUMINA integer coordinates to box units: pos = box * int / 2^32.
static py::array_t<double> convert_int_coords(py::array_t<uint32_t, py::array::c_style | py::array::forcecast> arr,
                                              double box, int nthreads) {
    if (nthreads <= 0) nthreads = effective_threads();
    std::vector<py::ssize_t> shape(arr.shape(), arr.shape() + arr.ndim());
    py::array_t<double> out(shape);
    const uint32_t* src = arr.data();
    double* dst = out.mutable_data();
    const int64_t n = (int64_t)arr.size();
    const double factor = box / 4294967296.0;  // 2^32

    py::gil_scoped_release nogil;
    int nt = (int)std::min<int64_t>(std::max(1, nthreads), std::max<int64_t>(1, n / (1 << 20)) );
    std::vector<std::thread> threads;
    auto convert = [&](int64_t lo, int64_t hi) {
        for (int64_t i = lo; i < hi; ++i) dst[i] = factor * (double)src[i];
    };
    int64_t step = (n + nt - 1) / nt;
    for (int t = 1; t < nt; ++t)
        threads.emplace_back(convert, t * step, std::min(n, (t + 1) * step));
    convert(0, std::min(n, step));
    for (auto& th : threads) th.join();
    return out;
}

static py::dict dataset_info(const std::string& path, const std::string& dset_name) {
    DatasetMeta m;
    {
        py::gil_scoped_release nogil;
        std::lock_guard<std::mutex> lock(h5_mutex);
        hid_t file = open_quiet(path);
        H5Closer fc{H5Fclose, file};
        hid_t dset = H5Dopen2(file, dset_name.c_str(), H5P_DEFAULT);
        if (dset < 0) throw std::runtime_error("lumina_core: no dataset '" + dset_name + "' in " + path);
        H5Closer dc{H5Dclose, dset};
        m = get_meta_locked(dset);
    }
    py::dict d;
    py::tuple shape(m.dims.size());
    for (size_t i = 0; i < m.dims.size(); ++i) shape[i] = (uint64_t)m.dims[i];
    d["shape"] = shape;
    d["dtype"] = m.dtype;
    d["layout"] = m.layout;
    d["nfilters"] = m.nfilters;
    if (!m.chunks.empty()) {
        py::tuple ch(m.chunks.size());
        for (size_t i = 0; i < m.chunks.size(); ++i) ch[i] = (uint64_t)m.chunks[i];
        d["chunks"] = ch;
    } else {
        d["chunks"] = py::none();
    }
    return d;
}

static std::vector<std::string> list_datasets(const std::string& path, const std::string& group) {
    std::vector<std::string> names;
    py::gil_scoped_release nogil;
    std::lock_guard<std::mutex> lock(h5_mutex);
    hid_t file = open_quiet(path);
    H5Closer fc{H5Fclose, file};
    hid_t grp = H5Gopen2(file, group.c_str(), H5P_DEFAULT);
    if (grp < 0) throw std::runtime_error("lumina_core: no group '" + group + "' in " + path);
    H5Closer gc{H5Gclose, grp};
    H5G_info_t info;
    H5Gget_info(grp, &info);
    for (hsize_t i = 0; i < info.nlinks; ++i) {
        ssize_t len = H5Lget_name_by_idx(grp, ".", H5_INDEX_NAME, H5_ITER_INC, i, nullptr, 0, H5P_DEFAULT);
        if (len <= 0) continue;
        std::string name(len + 1, '\0');
        H5Lget_name_by_idx(grp, ".", H5_INDEX_NAME, H5_ITER_INC, i, name.data(), len + 1, H5P_DEFAULT);
        name.resize(len);
        names.push_back(name);
    }
    return names;
}

PYBIND11_MODULE(_core, mod) {
    mod.doc() = "lumina_io C++ core: parallel HDF5 reads";
    // we report failures via exceptions; keep libhdf5's error stack quiet
    H5Eset_auto2(H5E_DEFAULT, nullptr, nullptr);
    mod.def("read", &read_rows, py::arg("path"), py::arg("dataset"),
            py::arg("start") = 0, py::arg("count") = -1, py::arg("nthreads") = 0,
            "Read rows [start, start+count) along axis 0 of a dataset.");
    mod.def("read_multi", &read_multi, py::arg("path"), py::arg("dataset"),
            py::arg("starts"), py::arg("counts"), py::arg("nthreads") = 0,
            "Read many row ranges in one parallel pass; rows are concatenated "
            "along axis 0 in the order given.");
    mod.def("read_box", &read_box, py::arg("path"), py::arg("dataset"),
            py::arg("starts"), py::arg("counts"), py::arg("nthreads") = 0,
            "Read the N-d sub-box [starts[d], starts[d]+counts[d]) (one entry "
            "per axis; count -1 = to the end). Parallel raw chunk reads when "
            "possible, serialized hyperslab H5Dread otherwise.");
    mod.def("convert_int_coords", &convert_int_coords, py::arg("arr"),
            py::arg("box"), py::arg("nthreads") = 0,
            "Convert uint32 integer coordinates to box units: box * i / 2^32.");
    mod.def("dataset_info", &dataset_info, py::arg("path"), py::arg("dataset"));
    mod.def("list_datasets", &list_datasets, py::arg("path"), py::arg("group") = "/");
    mod.def("set_num_threads", [](int n) { g_num_threads = n; }, py::arg("n"));
    mod.def("get_num_threads", []() { return effective_threads(); });
}
