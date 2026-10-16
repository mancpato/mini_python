def main():
    n = 90817
    suma = 0
    for k in range(0, n + 1):
        if n > 0:
            suma = suma + n % 10
            n = n // 10
    print(suma)

main()
