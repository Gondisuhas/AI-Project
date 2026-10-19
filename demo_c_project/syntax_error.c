// C program with a syntax error (missing semicolon)
#include <stdio.h>

int multiply(int a, int b) {
    return a * b
}

int main() {
    printf("Result: %d\n", multiply(4, 7));
    return 0;
}
