import base64

ENCRYPT_KEY = "enn-ai-coding-2026"


def encrypt_token(raw_token: str, key: str = ENCRYPT_KEY) -> str:
    """对 repo_token 进行 XOR + Base64 简单加密。

    Args:
        raw_token: 原始 token 字符串。
        key: 加密密钥，默认为 ``ENCRYPT_KEY``。

    Returns:
        Base64 编码后的加密字符串，适合在 URL 中安全传输。
    """
    result = bytearray()
    for i, ch in enumerate(raw_token):
        xor_val = ord(ch) ^ ord(key[i % len(key)])
        result.append(xor_val)
    return base64.b64encode(result).decode("ascii")


if __name__ == "__main__":
    # 测试：使用示例 token 验证加密结果
    test_token = "glpat-iNRdzAY8d98QBCsPhK3E"
    encrypted = encrypt_token(test_token)
    print(f"原始 token: {test_token}")
    print(f"加密结果: {encrypted}")
