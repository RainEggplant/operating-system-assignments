#include <stdio.h>

int main(void) {
  FILE *fp = fopen("/dev/mypipe_in", "w");
  char input[4096];
  while (scanf("%s", input)) {
    fprintf(fp, "%s\n", input);
    fflush(fp);
  }
}
