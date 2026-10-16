def main():
    a = 1071
    b = 462
    for k in range(0, b):
        if b != 0:
            r = a % b
            a = b
            b = r
    print(a)

main()
