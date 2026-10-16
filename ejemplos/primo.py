def main():
    n = 97
    divisores = 0
    for d in range(1, n + 1):
        if n % d == 0:
            divisores = divisores + 1
    if divisores == 2:
        print(1)
    else:
        print(0)

main()
