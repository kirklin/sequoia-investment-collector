import json
import re

# 检查点文件路径
checkpoint_file = 'scraper_checkpoint.json'

# 读取检查点文件
with open(checkpoint_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 清理公司名称，去除前面的数字编号
count = 0
for company in data['companies']:
    original_name = company['name']
    # 清理前缀数字
    cleaned_name = re.sub(r'^(\d+\s+)', '', original_name)
    
    if original_name != cleaned_name:
        count += 1
        print(f"修改: {original_name} -> {cleaned_name}")
        company['name'] = cleaned_name

# 保存修改后的文件
with open(checkpoint_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'检查了 {len(data["companies"])} 家公司名称，清理了 {count} 家公司名称') 
