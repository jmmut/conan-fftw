from conans import ConanFile, CMake, tools, ConfigureEnvironment
import os
import shutil
import subprocess
from glob import glob


class FFTWConan(ConanFile):
    VERSION_MAJOR = 3
    VERSION_MINOR = 3
    VERSION_PATCH = 4
    ZIP_FOLDER_NAME = 'fftw-%s.%s.%s' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

    name = 'fftw'
    version = '%s.%s.%s' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
    url = "https://github.com/kbinani/conan-fftw"
    settings = "os", "compiler", "build_type", "arch"
    options = {"static": [True, False]}
    default_options = "static=False"
    exports = "CMakeLists.txt", "config.h.cmake", "config.h.cmaketemplate", "conanfile.py"
    generators = "cmake"

    def source(self):
        targzfile = '%s.tar.gz' % self.ZIP_FOLDER_NAME
        tools.download("http://www.fftw.org/fftw-%s.tar.gz" % self.version, targzfile)
        tools.check_md5(targzfile, "2edab8c06b24feeb3b82bbb3ebf3e7b3")
        tools.untargz(targzfile)
        os.unlink(targzfile)

        shutil.move("CMakeLists.txt", self.ZIP_FOLDER_NAME)
        shutil.move("config.h.cmake", self.ZIP_FOLDER_NAME)
        shutil.move("config.h.cmaketemplate", self.ZIP_FOLDER_NAME)

    def build(self):
        if self.settings.os == "Windows":
            cmake = CMake(self.settings)

            args = ['-DBUILD_SHARED_LIBS=%s' % ('OFF' if self.options.static else 'ON')]
            args += ['-DCMAKE_INSTALL_PREFIX=.']
            self.run('cd %s && cmake . %s %s ' % (self.ZIP_FOLDER_NAME, ' '.join(args), cmake.command_line))

            self.run('cd %s && cmake --build . --target INSTALL %s' % (self.ZIP_FOLDER_NAME, cmake.build_config))
        else:
            prefix = os.path.join(os.getcwd(), self.ZIP_FOLDER_NAME)
            concurrency = 1
            try:
                import multiprocessing
                concurrency = multiprocessing.cpu_count()
            except (ImportError, NotImplementedError):
                pass

            base_args = ['--disable-fortran', '--disable-dependency-tracking', '--enable-threads', '--prefix=%s' % prefix]
            
            if self.options.static:
                base_args += ['--disable-shared', '--enable-static']
            else:
                base_args += ['--enable-shared', '--disable-static']

            if self.settings.build_type == 'Release':
                base_args += ['--disable-debug']
            else:
                base_args += ['--enable-debug']

            env = ConfigureEnvironment(self.deps_cpp_info, self.settings)

            precision_option = {'single': '--enable-single', 'double': '', 'long double': '--enable-long-double'}
            suffix = {'single': 'f', 'double': '', 'long double': 'l'}

            for precision in ['single', 'double', 'long double']:
                args = base_args + [precision_option[precision]]
                self.run('cd %s && %s ./configure %s' % (self.ZIP_FOLDER_NAME, env.command_line, ' '.join(args)))
                self.run('cd %s && make -j %s'        % (self.ZIP_FOLDER_NAME, concurrency))
                self.run('cd %s && make install'      % self.ZIP_FOLDER_NAME)

                # Copy 'tests/bench' (or 'tests/.libs/bench') to 'bin/bench{,f,l}'
                bench_name = 'bench%s' % suffix[precision]
                bench_dest = os.path.join(self.ZIP_FOLDER_NAME, 'bin', bench_name)
                bench = os.path.join(self.ZIP_FOLDER_NAME, 'tests', '.libs', 'bench')
                if not os.path.isfile(bench):
                    bench = os.path.join(self.ZIP_FOLDER_NAME, 'tests', 'bench')
                shutil.copyfile(bench, bench_dest)

                self.run('cd %s && make clean' % self.ZIP_FOLDER_NAME)

            self.run('cd %s && chmod +x bin/bench*' % self.ZIP_FOLDER_NAME)

            for binary in glob('%s/bin/*' % prefix) + glob('%s/lib/*.dylib' % prefix):
                self._change_dylib_names(binary, prefix)

    def package(self):
        osname = str(self.settings.os)

        self.copy_headers('*.h', os.path.join(self.ZIP_FOLDER_NAME, 'include'))

        if osname == "Windows":
            self.copy("bench*.exe", "bin", os.path.join(self.ZIP_FOLDER_NAME, "bin"), keep_path = False)
            self.copy("fftw*.dll", "bin", os.path.join(self.ZIP_FOLDER_NAME, "bin"), keep_path = False)
        else:
            self.copy('bench*', 'bin', os.path.join(self.ZIP_FOLDER_NAME, 'bin'), keep_path = False)
            self.copy('fftw*-wisdom*', 'bin', os.path.join(self.ZIP_FOLDER_NAME, 'bin'), keep_path = False)

        # "'Windows': 'lib'" is for import library files. DLL files are exist in 'bin' directory.
        shared_lib_extension = {'Windows': 'lib', 'Macos': 'dylib', 'Linux': 'so*'}

        static_lib_extension = {'Windows': 'lib', 'Macos': 'a',     'Linux': 'a'}

        if self.options.static:
            self.copy('*.%s' % static_lib_extension[osname], 'lib', os.path.join(self.ZIP_FOLDER_NAME, 'lib'), keep_path = False)
        else:
            self.copy('*.%s' % shared_lib_extension[osname], 'lib', os.path.join(self.ZIP_FOLDER_NAME, 'lib'), keep_path = False)

    def package_info(self):
        body = "fftw%s" % self.VERSION_MAJOR
        prefix = ""
        suffix_list = [""]
        osname = str(self.settings.os)
        if osname == "Windows":
            prefix = ""
            suffix_list = [""]
        elif osname == "Macos":
            prefix = "lib"
            suffix_list = [".a", "_threads.a"] if self.options.static else [".dylib", "_threads.dylib"]
        else:
            prefix = "lib"
            suffix_list = [".a", "_threads.a"] if self.options.static else [".so", "_threads.so"]

        self.cpp_info.libs = []
        for precision in ["", "f", "l"]:
            for suffix in suffix_list:
                name = prefix + body + precision + suffix
                self.cpp_info.libs += [name]

    def _change_dylib_names(self, file, base_directory):
        otool = 'otool -L "%s"' % file
        p = subprocess.Popen(otool, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        stdout_data, stderr_data = p.communicate()
        if not base_directory.endswith("/"):
            base_directory = base_directory + "/"
        for line in str(stdout_data).splitlines():
            line = str(line).strip()
            if line.endswith(":"):
                continue
            if not line.startswith(base_directory):
                continue
            ext = ".dylib"
            index = line.rfind(ext)
            dylib = line[0:index] + ext
            if dylib == file:
                continue
            name = '@executable_path/' + os.path.basename(dylib)
            subprocess.call(['install_name_tool', '-change', dylib, name, file])
