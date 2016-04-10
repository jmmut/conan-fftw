from conans import ConanFile, CMake
import os


class FFTWTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    requires = "fftw/3.3.4@kbinani/testing"
    generators = "cmake"

    def build(self):
        cmake = CMake(self.settings)
        self.run('cmake . %s' % cmake.command_line)
        self.run("cmake --build . %s" % cmake.build_config)

    def imports(self):
        self.copy("libfftw*.dylib", "lib", "bin")
        self.copy("fftw*.dll", "bin", "bin")
        self.copy("bench*", "bin", "bin")

    def test(self):
        # Run 'Testing' binary.
        if self.settings.os == "Linux":
            env = "LD_LIBRARY_PATH=./"
        else:
            env = ""
        executable = os.path.join(".", "bin", "Testing")
        command = "%s %s" % (env, executable)
        self.run(command)

        # Run bench for each precision.
        for precision in ("", "f", "l"):
        	bench_executable = "%s%s" % (os.path.join(".", "bin", "bench"), precision)
	        self.run("%s %s 64" % (env, bench_executable))
