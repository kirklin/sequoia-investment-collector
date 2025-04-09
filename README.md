# 红杉投资公司数据采集器 (Sequoia Investment Data Collector)

这是一个用于采集红杉资本投资组合公司数据的爬虫工具，支持从红杉中国和红杉全球官方网站获取投资公司信息。

## 项目介绍

本项目通过网络爬虫技术，从红杉资本官方网站采集投资组合公司的详细信息，包括公司名称、描述、行业分类、投资阶段等数据，并将这些信息整理为结构化数据保存。

## 功能特点

- ✅ 采集红杉中国投资的公司信息
- ✅ 采集红杉全球投资的公司信息
- 🔄 自动下载并保存公司logo图片
- 📊 自动提取和标准化行业分类信息
- 🔍 尝试从公司描述中提取投资阶段信息
- 💾 将采集的数据以结构化方式保存到Excel文件
- ⚙️ 支持命令行参数控制采集行为
- 🔁 支持断点续采功能

## 安装

本项目使用uv作为包管理工具，安装依赖前请确保已安装uv。

```bash
# 安装uv (如果尚未安装)
curl -sSf https://astral.sh/uv/install.sh | sh

# 克隆仓库
git clone https://github.com/yourusername/sequoia-investment-collector.git
cd sequoia-investment-collector

# 创建虚拟环境并安装依赖
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# 或者 .venv\Scripts\activate  # Windows
uv pip install -e .
```

## 使用方法

```bash
# 采集红杉中国的投资公司
python main.py

# 采集红杉全球的投资公司
python main.py --hsgcap

# 同时采集红杉中国和红杉全球的投资公司
python main.py --hongshan --hsgcap

# 指定输出文件路径
python main.py --output data/companies.xlsx

# 从上次中断的地方恢复采集
python main.py --resume

# 不搜索额外的公司ID
python main.py --no-extra

# 指定ID范围进行采集
python main.py --start-id 1000 --end-id 2000
```

## 输出数据字段说明

- `company_id`: 公司ID
- `name`: 公司名称
- `description`: 公司描述
- `industry`: 行业分类（已标准化）
- `investment_stage`: 投资阶段（从描述中提取）
- `source`: 数据来源（如"红杉中国"、"红杉全球"）
- `url`: 公司详情页URL
- `logo_url`: 公司logo图片URL
- `logo_path`: 本地保存的logo图片路径
- `crawl_date`: 数据采集日期

## 网站结构差异说明

红杉中国与红杉全球的网站结构有较大差异：
- 红杉中国(Hongshan)使用基于ID和AJAX的方式呈现公司信息
- 红杉全球(HSG)使用表格结构并有可折叠的详情部分

本爬虫工具已针对两种不同结构进行了适配，可单独采集任一网站或同时采集两个网站的数据。

## 注意事项

- 本工具仅采集公开已知的信息，不会尝试获取或破解任何非公开数据
- 网站结构可能会变化，如遇采集失败，请更新爬虫代码
- 请合理控制采集频率，避免对目标网站造成过大负担
- 采集的数据仅用于个人研究，请勿用于商业用途

## 许可证

MIT 
