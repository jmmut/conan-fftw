# coding: utf-8
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
    options = {"shared": [True, False]}
    default_options = "shared=False"
    exports = "CMakeLists.txt", "config.h.cmake", "config.h.cmaketemplate", "conanfile.py"
    generators = "cmake"
    license = "GNU General Public License: http://www.fftw.org/doc/License-and-Copyright.html"

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

            args = ['-DBUILD_SHARED_LIBS=%s' % ('ON' if self.options.shared else 'OFF')]
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
            
            if self.options.shared:
                base_args += ['--enable-shared', '--disable-static']
            else:
                base_args += ['--disable-shared', '--enable-static']

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
                if os.path.islink(binary):
                    continue
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

        if self.options.shared:
            copied_files = self.copy('*.%s' % shared_lib_extension[osname], 'lib', os.path.join(self.ZIP_FOLDER_NAME, 'lib'), keep_path = False)
        else:
            copied_files = self.copy('*.%s' % static_lib_extension[osname], 'lib', os.path.join(self.ZIP_FOLDER_NAME, 'lib'), keep_path = False)

        if not osname == "Windows" and len(copied_files) > 0:
            # Restore symlink under the package directory.
            # This process is required because self.copy does not keep symlinks.
            package_id = os.path.basename(os.getcwd())
            package_directory = copied_files[0].split(os.path.sep) # ~/.conan/data/fftw/3.3.4/#{username}/#{channel}/pacakge/#{package_id}/lib/libfftw3.dylib
            package_directory.pop() # pop "libfftw3.dylib"
            package_directory.pop() # pop "lib"
            package_directory = os.path.sep.join(package_directory) # ~/.conan/data/fftw/3.3.4/#{username}/#{channel}/package/#{package_id}
            build_directory = os.path.join(os.getcwd(), self.ZIP_FOLDER_NAME) # ~/.conan/data/fftw/3.3.4/#{username}/#{channel}/build/#{package_id}
            for file in copied_files:
                relative_path = os.path.relpath(file, package_directory) # lib/libfftw3.dylib
                source_file = os.path.join(build_directory, relative_path) # ~/.conan/data/fftw/3.3.4/#{username}/#{channel}/build/#{package_id}/fftw-3.3.4/lib/libfftw3.dylib
                if os.path.islink(source_file):
                    link_target_path = os.path.realpath(source_file) # ~/.conan/data/fftw/3.3.4/#{username}/#{channel}/build/#{package_id}/fftw-3.3.4/lib/libfftw3.3.dylib
                    os.unlink(file)

                    source_file_elements = source_file.split(os.path.sep)
                    source_file_elements.pop() # pop "libfftw3.dylib"
                    symlink_source = os.path.relpath(link_target_path, os.path.sep.join(source_file_elements)) # libfftw3.3.dylib

                    os.symlink(symlink_source, file)

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
            suffix_list = [".dylib", "_threads.dylib"] if self.options.shared else [".a", "_threads.a"]
        else:
            prefix = "lib"
            suffix_list = [".so", "_threads.so"] if self.options.shared else [".a", "_threads.a"]

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
            name = '@executable_path/' + os.path.basename(dylib)
            if dylib == file:
                subprocess.call(['install_name_tool', '-id', name, file])
            else:
                subprocess.call(['install_name_tool', '-change', dylib, name, file])
