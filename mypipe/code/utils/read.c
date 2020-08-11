#include <stdio.h>

int main(void) {
  char output[4096];
  FILE *fp = fopen("/dev/mypipe_out", "r");
  while (fscanf(fp, "%s", output)) {
    printf("%s\n", output);
  }
}
