project(Testing)
cmake_minimum_required(VERSION 2.8.12)

include(conanbuildinfo.cmake)
conan_basic_setup()

if(MSVC)
  add_definitions(/MP) # enable parallel compile
endif()

add_executable(Testing test.cpp)
target_link_libraries(Testing ${CONAN_LIBS})
