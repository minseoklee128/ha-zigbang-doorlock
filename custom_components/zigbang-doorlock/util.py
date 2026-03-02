import random

def generate_random_imei() -> str:
    """
    표준 규격(Luhn 알고리즘)을 따르는 15자리 랜덤 IMEI를 생성합니다.
    """
    # 1. 처음 14자리를 랜덤하게 생성 (TAC + Serial Number)
    # 실제로는 특정 제조사의 TAC 코드를 사용할 수도 있지만, 여기서는 랜덤으로 처리합니다.
    imei_digits = [random.randint(0, 9) for _ in range(14)]

    # 2. Luhn 알고리즘을 사용하여 마지막 15번째 검증 번호(Check Digit) 계산
    checksum = 0
    for i, digit in enumerate(imei_digits):
        # 오른쪽에서 두 번째 자리부터 시작하여(여기서는 인덱스 기준 짝/홀수 처리)
        # 역순으로 계산하는 것이 정석이나, 14자리 고정이므로 인덱스로 처리 가능합니다.
        # 짝수 인덱스(실제로는 홀수 번째 자리)는 그대로 더함
        # 홀수 인덱스(실제로는 짝수 번째 자리)는 2를 곱함
        if (i + 1) % 2 == 0: # 짝수 번째 자리 (인덱스 1, 3, 5...)
            doubled = digit * 2
            checksum += doubled if doubled < 10 else doubled - 9
        else:
            checksum += digit

    # 3. Check Digit 계산 (10 - (checksum % 10)) % 10
    check_digit = (10 - (checksum % 10)) % 10

    imei_digits.append(check_digit)

    return "".join(map(str, imei_digits))
