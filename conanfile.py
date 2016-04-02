from conans import ConanFile, CMake, tools
import os
import shutil

class Fftw3Conan(ConanFile):
    VERSION_MAJOR = 3
    VERSION_MINOR = 3
    VERSION_PATCH = 4
    ZIP_FOLDER_NAME = 'fftw-%s.%s.%s' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

    name = 'fftw%s' % VERSION_MAJOR
    version = '%s.%s.%s' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
    url = "https://github.com/kbinani/conan-fftw3"
    settings = "os", "compiler", "build_type", "arch"
    options = {"static": [True, False]}
    default_options = "static=False"
    exports = "CMakeLists.txt", "config.h.cmake", "config.h.cmaketemplate"

    def source(self):
        targzfile = "fftw-%s.tar.gz" % self.version
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

            args = ['-DBUILD_SHARED_LIBS=%s' % (self.options.static and 'OFF' or 'ON')]
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

            precision_option = {'single': '--enable-single', 'double': '', 'long double': '--enable-long-double'}
            for precision in ['single', 'double', 'long double']:
                args = base_args + [precision_option[precision]]
                self.run('cd %s && ./configure %s' % (self.ZIP_FOLDER_NAME, ' '.join(args)))
                self.run('cd %s && make -j %s'     % (self.ZIP_FOLDER_NAME, concurrency))
                self.run('cd %s && make install'   % self.ZIP_FOLDER_NAME)
                self.run('cd %s && make clean'     % self.ZIP_FOLDER_NAME)

    def package(self):
        self.copy_headers('*.h', os.path.join(self.ZIP_FOLDER_NAME, 'include'))
        self.copy('*', 'bin', os.path.join(self.ZIP_FOLDER_NAME, 'bin'), keep_path = False)

        # "'Windows': 'lib'" is for import library files. DLL files are exist in 'bin' directory.
        shared_lib_extension = {'Windows': 'lib', 'Macos': 'dylib', 'Linux': 'so'}

        static_lib_extension = {'Windows': 'lib', 'Macos': 'a',     'Linux': 'a'}
        osname = str(self.settings.os)

        if self.options.static:
            self.copy('*.%s' % static_lib_extension[osname], 'lib', os.path.join(self.ZIP_FOLDER_NAME, 'lib'), keep_path = False)
        else:
            self.copy('*.%s' % shared_lib_extension[osname], 'lib', os.path.join(self.ZIP_FOLDER_NAME, 'lib'), keep_path = False)

    def package_info(self):
        body = "fftw%s" % self.VERSION_MAJOR
        prefix = ""
        suffix_list = [""]

        if self.settings.os == "Windows":
            prefix = ""
            suffix_list = [""]
        if self.settings.os == "Macos":
            prefix = "lib"
            suffix_list = [".dylib", "_threads.dylib"] if self.options.static else [".a", "_threads.a"]
        else:
            prefix = "lib"
            suffix_list = [".so.3"]

        libs = []
        for precision in ["", "f", "l"]:
            for suffix in suffix_list:
                libs += [prefix + body + precision + suffix]
        self.cpp_info.libs = libs
