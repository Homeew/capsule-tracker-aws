cmake_minimum_required(VERSION 3.18)
project(capsule-tracker-aws LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# Reuse the research code (dipole model, sensor array, trajectory, LM solver)
# straight from the capsule-tracker repository.
include(FetchContent)
FetchContent_Declare(capsule_tracker
    GIT_REPOSITORY https://github.com/Homeew/capsule-tracker.git
    GIT_TAG        main)
FetchContent_MakeAvailable(capsule_tracker)

add_executable(sim_node sim_node.cpp)
target_link_libraries(sim_node PRIVATE tracker_lib)

add_executable(tracker_node tracker_node.cpp)
target_link_libraries(tracker_node PRIVATE tracker_lib)
