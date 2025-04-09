import argparse
import os
import pandas as pd
from sequoia_tracker.scraper import scrape_hongshan, scrape_hsgcap
from sequoia_tracker.data_processor import process_data
from sequoia_tracker.data_storage import save_to_excel


def parse_args():
    parser = argparse.ArgumentParser(description="红杉投资公司数据采集器")
    parser.add_argument(
        "--output", type=str, default="sequoia_companies.xlsx", help="输出Excel文件路径"
    )
    parser.add_argument(
        "--hongshan", action="store_true", help="采集红杉中国投资的公司"
    )
    parser.add_argument(
        "--hsgcap", action="store_true", help="采集红杉全球投资的公司"
    )
    
    # 添加控制ID搜索的参数
    parser.add_argument(
        "--start-id", type=int, help="开始搜索的ID（用于额外搜索）"
    )
    parser.add_argument(
        "--end-id", type=int, help="结束搜索的ID（用于额外搜索）"
    )
    parser.add_argument(
        "--no-extra", action="store_true", help="不搜索额外的公司ID"
    )
    parser.add_argument(
        "--resume", action="store_true", help="从上次中断的地方恢复爬取"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # 默认只爬取红杉中国
    if not args.hongshan and not args.hsgcap:
        args.hongshan = True
    
    all_companies = []
    
    if args.hongshan:
        print("正在爬取红杉中国投资的公司...")
        
        # 设置爬虫参数
        hongshan_companies = scrape_hongshan(
            start_id=args.start_id, 
            end_id=args.end_id,
            explore_additional=not args.no_extra,
            resume=args.resume
        )
        
        if hongshan_companies:
            processed_hongshan = process_data(hongshan_companies, source="红杉中国")
            all_companies.extend(processed_hongshan)
            print(f"已爬取红杉中国投资公司 {len(processed_hongshan)} 家")
    
    if args.hsgcap:
        print("正在爬取红杉全球投资的公司...")
        hsgcap_companies = scrape_hsgcap()
        if hsgcap_companies:
            processed_hsgcap = process_data(hsgcap_companies, source="红杉全球")
            all_companies.extend(processed_hsgcap)
            print(f"已爬取红杉全球投资公司 {len(processed_hsgcap)} 家")
    
    if all_companies:
        df = pd.DataFrame(all_companies)
        save_to_excel(df, args.output)
        print(f"数据已保存到 {args.output}")
    else:
        print("未获取到任何公司数据")


if __name__ == "__main__":
    main()
