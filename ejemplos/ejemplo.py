def main():
    suma = 0
    for i in range(1, 11):
        if i % 2 == 0:
            suma = suma + i
        else:
            suma = suma - 1
    print(suma)

main()
