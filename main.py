from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess


def run_crawler():
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    process.crawl('busca')
    
    process.start()


def main():
    run_crawler()


if __name__ == '__main__':
    main()
