# coding: utf-8
from conan.packager import ConanMultiPackager
import platform


if __name__ == "__main__":
    builder = ConanMultiPackager(username = "kbinani")

    if platform.system() == "Windows":
        for compiler_version in ["11", "12", "14"]:
            for compiler_runtime in ["MT", "MD"]:
                for build_type in ["Release", "Debug"]:
                    for arch in ["x86", "x86_64"]:
                        for shared in ["True", "False"]:
                            settings = {}
                            settings["compiler"] = "Visual Studio"
                            settings["compiler.version"] = compiler_version
                            settings["build_type"] = build_type
                            settings["compiler.runtime"] = "%s%s" % (compiler_runtime, "d" if build_type == "Debug" else "")
                            settings["arch"] = arch

                            options = {}
                            options["fftw:shared"] = shared

                            builder.add(settings, options)
    else:
        for build_type in ["Release", "Debug"]:
            for shared in ["True", "False"]:
                settings = {}
                settings["build_type"] = build_type

                options = {}
                options["fftw:shared"] = shared

                builder.add(settings, options)

    builder.run()
