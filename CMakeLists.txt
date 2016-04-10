cmake_minimum_required(VERSION 3.0)
project(fftw)

option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

include(../conanbuildinfo.cmake)
conan_basic_setup()

add_definitions(-D_CRT_SECURE_NO_WARNINGS)
add_definitions(/Oi) # enable intrinsic functions
add_definitions(/MP) # enable parallel compile
add_definitions(/wd4244 /wd4267 /wd4819)

include(FindOpenMP)
if(OPENMP_FOUND)
  set(HAVE_OPENMP true)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
  set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
else()
  set(HAVE_OPENMP)
endif()

if(CMAKE_SIZEOF_VOID_P MATCHES 8)
  set(project_arch "x86_64")
else()
  set(project_arch "x86")
endif()

function(setup_source_groups source_file_list project_root_dir)
  get_filename_component(project_root_dir "${project_root_dir}" ABSOLUTE)
  string(REPLACE "\\" "/" project_root_dir "${project_root_dir}")
  foreach(original_source_file_path ${source_file_list})
    get_filename_component(source_file_path "${original_source_file_path}" ABSOLUTE)
    string(REPLACE "\\" "/" source_file_path "${source_file_path}")
    string(REGEX REPLACE "^${project_root_dir}/" "" relative_path "${source_file_path}")
    # extract directory name
    get_filename_component(dirname "${relative_path}" DIRECTORY)
    # replace "/" to "\\"
    string(REPLACE "/" "\\" group_name "${dirname}")
    source_group("${group_name}" FILES "${source_file_path}")
  endforeach()
endfunction()

set(precisions long-double double float)
foreach(precision ${precisions})
  set(HAVE_SSE2)
  set(FFTW_SINGLE)
  set(FFTW_LDOUBLE)
  set(BENCHFFT_SINGLE)
  set(BENCHFFT_LDOUBLE)

  if(${precision} STREQUAL "float")
    set(suffix "f")
    set(HAVE_SSE2 true)
    set(FFTW_SINGLE 1)
    set(BENCHFFT_SINGLE 1)
  elseif(${precision} STREQUAL "long-double")
    set(suffix "l")
    set(FFTW_LDOUBLE 1)
    set(BENCHFFT_LDOUBLE 1)
  elseif(${precision} STREQUAL "double")
    set(suffix "")
    set(HAVE_SSE2 true)
  endif()

  set(lib_name fftw3${suffix})
  set(bench_name bench${suffix})

  file(GLOB_RECURSE lib_all_files
    "api/*.c"
    "api/*.h"
    "dft/scalar/*.c"
    "dft/scalar/*.h"
    "kernel/*.c"
    "kernel/*.h"
    "rdft/scalar/*.c"
    "rdft/scalar/*.h"
    "reodft/*.c"
    "reodft/*.h"
    "simd-support/*.c"
    "simd-support/*.h"
    "threads/*.c"
    "threads/*.h")
  file(GLOB lib_dft_files
    "dft/*.c"
    "dft/*.h"
    "rdft/*.c"
    "rdft/*.h")
  file(GLOB lib_dft_sse2_files
    "dft/simd/sse2/*.c"
    "dft/simd/sse2/*.h"
    "rdft/simd/sse2/*.c"
    "rdft/simd/sse2/*.h")
  file(GLOB bench_all_files
    "tests/*.c"
    "tests/*.h"
    "libbench2/*.c"
    "libbench2/*.h")

  list(APPEND lib_all_files ${lib_dft_files})
  list(REMOVE_ITEM bench_all_files ${CMAKE_CURRENT_SOURCE_DIR}/libbench2/useropt.c)

  if(HAVE_SSE2)
    list(APPEND lib_all_files ${lib_dft_sse2_files})
  endif()

  if(HAVE_OPENMP)
    list(REMOVE_ITEM lib_all_files ${CMAKE_CURRENT_SOURCE_DIR}/threads/threads.c)
  else()
    list(REMOVE_ITEM lib_all_files ${CMAKE_CURRENT_SOURCE_DIR}/threads/openmp.c)
  endif()

  if (${BUILD_SHARED_LIBS})
    add_library(${lib_name} SHARED ${lib_all_files})
  else()
    add_library(${lib_name} STATIC ${lib_all_files})
  endif()
  add_executable(${bench_name} ${bench_all_files})
  target_link_libraries(${bench_name} ${lib_name})

  setup_source_groups("${lib_all_files}" "${CMAKE_CURRENT_SOURCE_DIR}")
  setup_source_groups("${bench_all_files}" "${CMAKE_CURRENT_SOURCE_DIR}")

  # create config.h 
  set(config_directory ${CMAKE_CURRENT_SOURCE_DIR}/config/${lib_name})
  if(NOT EXISTS ${config_directory})
    execute_process(COMMAND ${CMAKE_COMMAND} -E make_directory ${config_directory})
  endif()
  include(config.h.cmake)

  set_property(TARGET ${lib_name} PROPERTY INCLUDE_DIRECTORIES
    ${config_directory}
    ${CMAKE_CURRENT_SOURCE_DIR}/api
    ${CMAKE_CURRENT_SOURCE_DIR}/dft
    ${CMAKE_CURRENT_SOURCE_DIR}/dft/scalar
    ${CMAKE_CURRENT_SOURCE_DIR}/dft/simd
    ${CMAKE_CURRENT_SOURCE_DIR}/kernel
    ${CMAKE_CURRENT_SOURCE_DIR}/rdft
    ${CMAKE_CURRENT_SOURCE_DIR}/rdft/scalar
    ${CMAKE_CURRENT_SOURCE_DIR}/rdft/simd
    ${CMAKE_CURRENT_SOURCE_DIR}/reodft
    ${CMAKE_CURRENT_SOURCE_DIR}/simd-support
    ${CMAKE_CURRENT_SOURCE_DIR}/threads)

  set_property(TARGET ${lib_name} PROPERTY COMPILE_DEFINITIONS
    LIBFFTWF33_EXPORTS)

  if(${BUILD_SHARED_LIBS})
    set_property(TARGET ${lib_name} PROPERTY COMPILE_DEFINITIONS
      FFTW_DLL)

    # "FFTW_DLL" is needed in spite of bench{,f,l}.exe itself is not a DLL.
    # Without "FFTW_DLL", link errors will given for symbols, "fftw_cc", "fftw_version", "fftw_codelet_optim".
    set_property(TARGET ${bench_name} PROPERTY COMPILE_DEFINITIONS
      FFTW_DLL)
  endif()

  set_property(TARGET ${bench_name} PROPERTY INCLUDE_DIRECTORIES
    ${config_directory}
    ${CMAKE_CURRENT_SOURCE_DIR}/api
    ${CMAKE_CURRENT_SOURCE_DIR}/dft
    ${CMAKE_CURRENT_SOURCE_DIR}/kernel
    ${CMAKE_CURRENT_SOURCE_DIR}/rdft
    ${CMAKE_CURRENT_SOURCE_DIR}/libbench2)

  if(HAVE_SSE2)
    # All x86_64 processors have SSE2, so "/arch:SSE2" is not needed.
    # In x86_64 build, compiler gives warnings like "warning D9002 : ignoring unknown option '/arch:SSE2'".
    if(project_arch STREQUAL "x86")
      add_definitions(/arch:SSE2)
    endif()
  endif()

  install(TARGETS ${lib_name} EXPORT ${PROJECT_NAME}-targets
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib)
  install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/api/fftw3.h DESTINATION include)
  install(TARGETS ${bench_name} RUNTIME DESTINATION bin)

endforeach()
