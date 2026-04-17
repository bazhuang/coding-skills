from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field
import os

# 初始化 FastMCP 服务
mcp = FastMCP("Graph Tools")


@mcp.tool()
def data_write(
        file_path: Annotated[
            str,
            Field(
                description="文件保存的绝对路径。必须包含文件名和扩展名。",
            )
        ],
        content: Annotated[
            str,
            Field(
                description="包含图谱数据（节点、边、属性）的完整 JSON 字符串。请确保格式符合 JSON 标准。",
                examples=[{"objects": [], "edges": []}]
            )
        ]
) -> str:
    """
    专用于将图谱相关的数据（节点、边、关系属性）以 JSON 格式写入文件。
    该工具不同于 'Write' 工具，它专门处理结构化的网络/图谱数据。
    当生成知识图谱、ER 图或网络拓扑图数据时，必须使用此工具而不是标准 Write 工具。
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(content)
            return content
    except Exception as e:
        return f"File created failed, error: {str(e)}"


if __name__ == "__main__":
    mcp.run()