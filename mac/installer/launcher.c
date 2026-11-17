/* Main executable of "Install LCA Wrench.app": runs Contents/Resources/bootstrap.sh with /bin/bash.
 *
 * An app needs a Mach-O main executable to be signed with the hardened runtime and notarized by Apple; a shell
 * script as main executable keeps its signature in extended attributes, which do not survive every way of unpacking
 * a zip. Built by pack_mac.sh (clang, arm64 and x86_64). */
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    char raw[PATH_MAX], exe[PATH_MAX], script[PATH_MAX];
    uint32_t size = sizeof raw;
    if (_NSGetExecutablePath(raw, &size) != 0 || realpath(raw, exe) == NULL) {
        fprintf(stderr, "Install LCA Wrench: cannot find its own path\n");
        return 1;
    }
    /* .../Contents/MacOS/<exe>  ->  .../Contents/Resources/bootstrap.sh */
    char *contents = dirname(dirname(exe));
    if (snprintf(script, sizeof script, "%s/Resources/bootstrap.sh", contents) >= (int)sizeof script) return 1;
    execl("/bin/bash", "bash", script, (char *)NULL);
    perror("Install LCA Wrench");
    return 1;
}
