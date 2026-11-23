// Simulated sensor stream: prints one JSON object per line.
//   ./sim_node [--rate 10] [--duration 20] [--noise-ut 0.05] [--seed 42]
#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>

#include "sensor_array.hpp"
#include "trajectory.hpp"

int main(int argc, char** argv) {
    double rate = 10.0, duration = 20.0, noiseUt = 0.05;
    unsigned seed = 42;
    for (int i = 1; i + 1 < argc; i += 2) {
        const std::string key = argv[i];
        if (key == "--rate") rate = std::atof(argv[i + 1]);
        else if (key == "--duration") duration = std::atof(argv[i + 1]);
        else if (key == "--noise-ut") noiseUt = std::atof(argv[i + 1]);
        else if (key == "--seed") seed = static_cast<unsigned>(std::atoi(argv[i + 1]));
    }

    const mag::SensorArray sensors = mag::twoLayerRing();
    const mag::GiTrajectory trajectory;
    std::mt19937 rng(seed);
    std::normal_distribution<double> noise(0.0, noiseUt);

    const long frames = static_cast<long>(duration * rate);
    for (long k = 0; k < frames; ++k) {
        const double t = k / rate;
        const mag::CapsuleState s = trajectory.at(t);
        const Eigen::VectorXd z = mag::measure(sensors, s.position, s.moment);

        std::printf("{\"t\": %.3f, \"true_position_m\": [%.6f, %.6f, %.6f], \"readings_ut\": [",
                    t, s.position.x(), s.position.y(), s.position.z());
        for (std::size_t i = 0; i < sensors.size(); ++i) {
            std::printf("%s[%.5f, %.5f, %.5f]", i ? ", " : "",
                        z(3 * i) + noise(rng), z(3 * i + 1) + noise(rng), z(3 * i + 2) + noise(rng));
        }
        std::printf("]}\n");
    }
    return 0;
}
