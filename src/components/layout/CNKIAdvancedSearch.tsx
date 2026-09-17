# tclConfig.sh --
#
# This shell script (for sh) is generated automatically by Tcl's
# configure script.  It will create shell variables for most of
# the configuration options discovered by the configure script.
# This script is intended to be included by the configure scripts
# for Tcl extensions so that they don't have to figure this all
# out for themselves.
#
# The information in this file is specific to a single platform.

TCL_DLL_FILE="tcl86t.dll"

# Tcl's version number.
TCL_VERSION='8.6'
TCL_MAJOR_VERSION='8'
TCL_MINOR_VERSION='6'
TCL_PATCH_LEVEL='8.6.15'

# C compiler to use for compilation.
TCL_CC='cl.exe'

# -D flags for use with the C compiler.
TCL_DEFS='-nologo -c /D_ATL_XP_TARGETING  /DHAVE_CPUID=1 -W3 -wd4090 -wd4146 -wd4311 -wd4312 -FpC:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\Release_AMD64_VC1929\tcl_ThreadedDynamic\  -fp:strict -O2 -GS -GL -MD -I"C:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\..\win" -I"C:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\..\generic"  -I"C:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\..\libtommath"  /DMP_PREC=4 /Dinline=__inline /DHAVE_ZLIB=1 /D_CRT_SECURE_NO_DEPRECATE /D_CRT_NONSTDC_NO_DEPRECATE /DMP_FIXED_CUTOFFS /DSTDC_HEADERS /DUSE_NMAKE=1 /DHAVE_STDINT_H=1 /DHAVE_INTTYPES_H=1 /DHAVE_STDBOOL_H=1 /DTCL_THREADS=1 /DUSE_THREAD_ALLOC=1 /DNDEBUG /DTCL_CFG_OPTIMIZED /DTCL_CFG_DO64BIT   /DBUILD_tcl'

# If TCL was built with debugging symbols, generated libraries contain
# this string at the end of the library name (before the extension).
TCL_DBGX=t

# Default flags used in an optimized and debuggable build, respectively.
TCL_CFLAGS_DEBUG='-nologo -c -W3 -YX -FpC:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\Release_AMD64_VC1929\tcl_ThreadedDynamic\ -MDd'
TCL_CFLAGS_OPTIMIZE='-nologo -c -W3 -YX -FpC:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\Release_AMD64_VC1929\tcl_ThreadedDynamic\ -MD'

# Default linker flags used in an optimized and debuggable build, respectively.
TCL_LDFLAGS_DEBUG='-nologo -machine:AMD64 -debug -debugtype:cv'
TCL_LDFLAGS_OPTIMIZE='-nologo -machine:AMD64 -release -opt:ref -opt:icf,3'

# Flag, 1: we built a shared lib, 0 we didn't
TCL_SHARED_BUILD=1

# The name of the Tcl library (may be either a .a file or a shared library):
TCL_LIB_FILE='tcl86t.lib'

# Flag to indicate whether shared libraries need export files.
TCL_NEEDS_EXP_FILE=''

# Deprecated. Same as TCL_UNSHARED_LIB_SUFFIX
TCL_EXPORT_FILE_SUFFIX='86t.lib'

# Additional libraries to use when linking Tcl.
TCL_LIBS='kernel32.lib advapi32.lib netapi32.lib user32.lib userenv.lib ws2_32.lib ucrt.lib netapi32.lib user32.lib userenv.lib ws2_32.lib'

# Top-level directory in which Tcl's platform-independent files are
# installed.
TCL_PREFIX='e:/pycharm/projects/Stressor-test/.conda\Library'

# Top-level directory in which Tcl's platform-specific files (e.g.
# executables) are installed.
TCL_EXEC_PREFIX='e:/pycharm/projects/Stressor-test/.conda\Library\bin'

# Flags to pass to cc when compiling the components of a shared library:
TCL_SHLIB_CFLAGS=''

# Flags to pass to cc to get warning messages
TCL_CFLAGS_WARNING='-W3'

# Extra flags to pass to cc:
TCL_EXTRA_CFLAGS='-YX'

# Base command to use for combining object files into a shared library:
TCL_SHLIB_LD='link -nologo -machine:AMD64  -ltcg -release -opt:ref -opt:icf,3 -nodefaultlib:libucrt.lib -dll'

# Base command to use for combining object files into a static library:
TCL_STLIB_LD='lib -nologo'

# Either '$LIBS' (if dependent libraries should be included when linking
# shared libraries) or an empty string.  See Tcl's configure.in for more
# explanation.
TCL_SHLIB_LD_LIBS='kernel32.lib advapi32.lib netapi32.lib user32.lib userenv.lib ws2_32.lib ucrt.lib netapi32.lib user32.lib userenv.lib ws2_32.lib'

# Suffix to use for the name of a shared library.
TCL_SHLIB_SUFFIX='.dll'

# Library file(s) to include in tclsh and other base applications
# in order to provide facilities needed by DLOBJ above.
TCL_DL_LIBS=''

# Flags to pass to the compiler when linking object files into
# an executable tclsh or tcltest binary.
TCL_LD_FLAGS=''

# Flags to pass to cc/ld, such as "-R /usr/local/tcl/lib", that tell the
# run-time dynamic linker where to look for shared libraries such as
# libtcl.so.  Used when linking applications.  Only works if there
# is a variable "LIB_RUNTIME_DIR" defined in the Makefile.
TCL_CC_SEARCH_FLAGS=''
TCL_LD_SEARCH_FLAGS=''

# Additional object files linked with Tcl to provide compatibility
# with standard facilities from ANSI C or POSIX.
TCL_COMPAT_OBJS=''

# Name of the ranlib program to use.
TCL_RANLIB=''

# -l flag to pass to the linker to pick up the Tcl library
TCL_LIB_FLAG='tcl86t.lib'

# String to pass to linker to pick up the Tcl library from its
# build directory.
TCL_BUILD_LIB_SPEC='C:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\Release_AMD64_VC1929\tcl86t.lib'

# String to pass to linker to pick up the Tcl library from its
# installed directory.
TCL_LIB_SPEC='e:/pycharm/projects/Stressor-test/.conda\Library\lib\tcl86t.lib'

# String to pass to the compiler so that an extension can
# find installed Tcl headers.
TCL_INCLUDE_SPEC='-Ie:/pycharm/projects/Stressor-test/.conda\Library\include'

# Indicates whether a version numbers should be used in -l switches
# ("ok" means it's safe to use switches like -ltcl7.5;  "nodots" means
# use switches like -ltcl75).  SunOS and FreeBSD require "nodots", for
# example.
TCL_LIB_VERSIONS_OK='nodots'

# String that can be evaluated to generate the part of a shared library
# name that comes after the "libxxx" (includes version number, if any,
# extension, and anything else needed).  May depend on the variables
# VERSION and SHLIB_SUFFIX.  On most UNIX systems this is
# ${VERSION}${SHLIB_SUFFIX}.
TCL_SHARED_LIB_SUFFIX='86t.dll'

# String that can be evaluated to generate the part of an unshared library
# name that comes after the "libxxx" (includes version number, if any,
# extension, and anything else needed).  May depend on the variable
# VERSION.  On most UNIX systems this is ${VERSION}.a.
TCL_UNSHARED_LIB_SUFFIX='86t.lib'

# Location of the top-level source directory from which Tcl was built.
# This is the directory that contains a README file as well as
# subdirectories such as generic, unix, etc.  If Tcl was compiled in a
# different place than the directory containing the source files, this
# points to the location of the sources, not the location where Tcl was
# compiled.
TCL_SRC_DIR='C:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\..'

# List of standard directories in which to look for packages during
# "package require" commands.  Contains the "prefix" directory plus also
# the "exec_prefix" directory, if it is different.
TCL_PACKAGE_PATH='e:/pycharm/projects/Stressor-test/.conda\Library\lib'

# Tcl supports stub.
TCL_SUPPORTS_STUBS=1

# The name of the Tcl stub library (.a):
TCL_STUB_LIB_FILE='tclstub86.lib'

# -l flag to pass to the linker to pick up the Tcl stub library
TCL_STUB_LIB_FLAG='tclstub86.lib'

# String to pass to linker to pick up the Tcl stub library from its
# build directory.
TCL_BUILD_STUB_LIB_SPEC='-LC:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\Release_AMD64_VC1929 tclstub86.lib'

# String to pass to linker to pick up the Tcl stub library from its
# installed directory.
TCL_STUB_LIB_SPEC='-Le:/pycharm/projects/Stressor-test/.conda\Library\lib tclstub86.lib'

# Path to the Tcl stub library in the build directory.
TCL_BUILD_STUB_LIB_PATH='C:\b\abs_933obpeb5t\croot\tk_1755243793210\work\tcl8.6.15\win\Release_AMD64_VC1929\tclstub86.lib'

# Path to the Tcl stub library in the install directory.
TCL_STUB_LIB_PATH='e:/pycharm/projects/Stressor-test/.conda\Library\lib\tclstub86.lib'

# Flag, 1: we built Tcl with threads enabled, 0 we didn't
TCL_THREADS=1

# Name of the zlib library that extensions should use
TCL_ZLIB_LIB_NAME='zdll.lib'
                                                                    <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SEARCH_FIELDS.map(field => (
                          <SelectItem key={field.value} value={field.value}>
                            {field.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {/* 检索词输入 */}
                    <Input
                      placeholder="输入检索词"
                      value={condition.value}
                      onChange={(e) => updateCondition(condition.id, 'value', e.target.value)}
                      className="flex-1 h-8 text-sm"
                    />

                    {/* 匹配方式 */}
                    <Select
                      value={condition.operator}
                      onValueChange={(value) => updateCondition(condition.id, 'operator', value)}
                    >
                      <SelectTrigger className="w-16 h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MATCH_TYPES.map(type => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {/* 操作按钮 */}
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={addCondition}
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                      {conditions.length > 1 && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => removeCondition(condition.id)}
                        >
                          <Minus className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            {/* 筛选选项区 */}
            <div className="space-y-3">
              <label className="text-sm font-medium">筛选选项</label>
              
              {/* 文献类型筛选 */}
              <div className="grid grid-cols-3 gap-3">
                <label className="flex items-center space-x-2 text-sm">
                  <Checkbox
                    checked={filters.oaPublishing}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({ ...prev, oaPublishing: !!checked }))
                    }
                  />
                  <span>OA出版</span>
                </label>
                <label className="flex items-center space-x-2 text-sm">
                  <Checkbox
                    checked={filters.webFirstPublishing}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({ ...prev, webFirstPublishing: !!checked }))
                    }
                  />
                  <span>网络首发</span>
                </label>
                <label className="flex items-center space-x-2 text-sm">
                  <Checkbox
                    checked={filters.enhancedPublishing}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({ ...prev, enhancedPublishing: !!checked }))
                    }
                  />
                  <span>增强出版</span>
                </label>
                <label className="flex items-center space-x-2 text-sm">
                  <Checkbox
                    checked={filters.fundedLiterature}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({ ...prev, fundedLiterature: !!checked }))
                    }
                  />
                  <span>基金文献</span>
                </label>
                <label className="flex items-center space-x-2 text-sm">
                  <Checkbox
                    checked={filters.chineseEnglishExpansion}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({ ...prev, chineseEnglishExpansion: !!checked }))
                    }
                  />
                  <span>中英文扩展</span>
                </label>
                <label className="flex items-center space-x-2 text-sm">
                  <Checkbox
                    checked={filters.synonymExpansion}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({ ...prev, synonymExpansion: !!checked }))
                    }
                  />
                  <span>同义词扩展</span>
                </label>
              </div>

              {/* 时间范围 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">时间范围</label>
                <div className="flex items-center gap-2">
                  <Select
                    value={timeRange.type}
                    onValueChange={(value) => setTimeRange(prev => ({ ...prev, type: value }))}
                  >
                    <SelectTrigger className="w-24 h-8 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIME_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "h-8 justify-start text-left font-normal text-sm w-32",
                          !startDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-1 h-3 w-3" />
                        {startDate ? format(startDate, "yyyy-MM-dd") : "开始日期"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={startDate}
                        onSelect={handleStartDateSelect}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>

                  <span className="text-sm text-muted-foreground">至</span>

                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "h-8 justify-start text-left font-normal text-sm w-32",
                          !endDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-1 h-3 w-3" />
                        {endDate ? format(endDate, "yyyy-MM-dd") : "结束日期"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={endDate}
                        onSelect={handleEndDateSelect}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>

                  <label className="flex items-center space-x-1 text-sm">
                    <Checkbox
                      checked={timeRange.unlimited}
                      onCheckedChange={(checked) => {
                        setTimeRange(prev => ({ ...prev, unlimited: !!checked }));
                        if (checked) {
                          setStartDate(undefined);
                          setEndDate(undefined);
                        }
                      }}
                    />
                    <span>不限</span>
                  </label>
                </div>
              </div>

              {/* 最大结果数 */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">最大结果数:</label>
                <Select
                  value={maxResults.toString()}
                  onValueChange={(value) => setMaxResults(parseInt(value))}
                >
                  <SelectTrigger className="w-20 h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                    <SelectItem value="200">200</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator />

            {/* 操作按钮 */}
            <div className="flex justify-between">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={resetAll}
                className="gap-1 text-sm"
              >
                <RotateCcw className="h-3 w-3" />
                重置条件
              </Button>
              
              <Button 
                onClick={handleSearch} 
                disabled={isLoading}
                className="gap-1 text-sm bg-orange-500 hover:bg-orange-600"
              >
                {isLoading ? (
                  <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <span>🔍</span>
                )}
                {isLoading ? "检索中..." : "检索"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </PopoverContent>
    </Popover>
  );
}
