import json
import os
from tqdm import tqdm


def convert_json_to_txt(json_file_path, txt_file_path):
    """
    将JSON格式的测试结果转换为TXT格式
    :param json_file_path: JSON文件路径
    :param txt_file_path: 输出的TXT文件路径
    """
    # 检查JSON文件是否存在
    if not os.path.exists(json_file_path):
        print(f"错误: JSON文件不存在 {json_file_path}")
        return False

    try:
        # 加载JSON数据
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"开始转换: {json_file_path} -> {txt_file_path}")
        print(f"共 {len(data)} 条数据")

        # 写入TXT文件
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            for i, item in enumerate(tqdm(data, desc="转换进度")):
                # 写入ID
                f.write(f'"id": {item.get("id", "N/A")},\n')

                # 写入内容（确保转义特殊字符）
                content = item.get("content", "")
                # 替换换行符为空格，确保单行显示
                content = content.replace("\n", " ").replace("\r", " ")
                f.write(f'"content": "{content}",\n')

                # 写入输出
                output = item.get("output", "")
                # 替换换行符为空格，确保单行显示
                output = output.replace("\n", " ").replace("\r", " ")
                f.write(f'"output": "{output}"\n\n')

        print(f"转换完成: {txt_file_path}")
        return True

    except Exception as e:
        print(f"转换过程中出错: {str(e)}")
        return False


def main():
    # 定义要转换的JSON文件列表
    json_files = [
        "test1_results.json",
        # "test2_results.json"
    ]

    # 创建输出目录
    output_dir = "txt_results"
    os.makedirs(output_dir, exist_ok=True)

    # 转换所有文件
    for json_file in json_files:
        # 构建输出文件路径
        txt_file = os.path.join(output_dir, json_file.replace(".json", ".txt"))

        # 执行转换
        success = convert_json_to_txt(json_file, txt_file)

        if success:
            # 预览部分内容
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:6]  # 读取前6行
                print("\n转换结果预览:")
                print(''.join(lines))
            except:
                pass
            print("-" * 50 + "\n")


if __name__ == "__main__":
    main()