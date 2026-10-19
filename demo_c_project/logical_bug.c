// C program with a logical bug (uninitialized variable)
#include <stdio.h>

int calculate_average(int sum, int count) {
    int average;
    // Bug: average is uninitialized before use
    printf("Average: %d\n", average);
    return sum / count;
}

int main() {
    int result = calculate_average(100, 5);
    printf("Result: %d\n", result);
    return 0;
}
