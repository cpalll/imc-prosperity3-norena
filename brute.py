import math

conversion = [[1, 1.45, 0.52, 0.72], [0.7, 1, 0.31, 0.48], [1.95, 3.1, 1, 1.49], [1.34, 1.98, 0.64, 1]]


for i in range(4):
    rate1 = 2 * conversion[3][i]
    for j in range(4):
        rate2 = conversion[i][j]
        for k in range(4):
            rate3 = conversion[j][k]
            for l in range(4):
                rate4 = conversion[k][l]
                rate5 = conversion[l][3]
                print(i, j, k, l)
                print(rate1 * rate2 * rate3 * rate4 * rate5)