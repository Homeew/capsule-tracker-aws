// Reads JSON lines (as written by sim_node) on stdin, estimates the capsule
// position and moment with the frame-by-frame LM solver, and prints one JSON
// line per frame. Each frame starts from the previous estimate (warm start).
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "lm_baseline.hpp"

// Read `count` numbers that follow `key` in `line`.
static bool numbersAfter(const std::string& line, const char* key,
                         std::size_t count, std::vector<double>& out) {
    const auto pos = line.find(key);
    if (pos == std::string::npos) return false;
    const char* p = line.c_str() + pos + std::strlen(key);
    out.clear();
    while (out.size() < count && *p) {
        if (std::isdigit(static_cast<unsigned char>(*p)) || *p == '-' || *p == '+' || *p == '.') {
            char* end = nullptr;
            const double v = std::strtod(p, &end);
            if (end == p) { ++p; continue; }
            out.push_back(v);
            p = end;
        } else {
            ++p;
        }
    }
    return out.size() == count;
}

int main() {
    const mag::SensorArray sensors = mag::twoLayerRing();
    const mag::LmBaseline solver(sensors);
    const std::size_t nMeas = 3 * sensors.size();

    mag::Vec3 p(0.02, 0.02, 0.02);   // initial guess
    mag::Vec3 m(0.1, 0.1, 0.1);

    std::string line;
    std::vector<double> t, truth, readings;
    while (std::getline(std::cin, line)) {
        if (!numbersAfter(line, "\"t\":", 1, t) ||
            !numbersAfter(line, "\"readings_ut\"", nMeas, readings)) {
            std::fprintf(stderr, "skipping malformed line\n");
            continue;
        }
        Eigen::VectorXd z(static_cast<Eigen::Index>(nMeas));
        for (std::size_t i = 0; i < nMeas; ++i) z(static_cast<Eigen::Index>(i)) = readings[i];

        const mag::LmResult r = solver.solve(z, p, m);
        p = r.position;
        m = r.moment;

        std::printf("{\"t\": %.3f, \"est_position_m\": [%.6f, %.6f, %.6f], "
                    "\"est_moment_am2\": [%.5f, %.5f, %.5f], \"cost\": %.6f, \"converged\": %s",
                    t[0], r.position.x(), r.position.y(), r.position.z(),
                    r.moment.x(), r.moment.y(), r.moment.z(), r.cost,
                    r.converged ? "true" : "false");
        if (numbersAfter(line, "\"true_position_m\"", 3, truth)) {
            const mag::Vec3 tp(truth[0], truth[1], truth[2]);
            std::printf(", \"error_mm\": %.4f", 1000.0 * (r.position - tp).norm());
        }
        std::printf("}\n");
        std::fflush(stdout);
    }
    return 0;
}
