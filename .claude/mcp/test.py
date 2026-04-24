from fastmcp import FastMCP
from typing import Annotated, AsyncGenerator
from pydantic import Field
import asyncio

# 初始化 FastMCP 服务
mcp = FastMCP("Test Tools")


@mcp.tool()
async def stream_test() -> AsyncGenerator[str, None]:
    """
    测试流式输出工具，自动输出100个字符串
    """
    for i in range(1, 11):
        yield f"第 {i} 条消息：这是流式输出测试\n"
        await asyncio.sleep(0.05)  # 每条消息间隔50毫秒，模拟真实流式输出


if __name__ == "__main__":
    mcp.run()