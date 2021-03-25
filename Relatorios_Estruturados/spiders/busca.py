import os
import time
import re

import scrapy
from scrapy.selector import Selector
from scrapy import signals
from scrapy import Spider

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from Relatorios_Estruturados.items import Item

class SpiderBusca(scrapy.Spider):
    name = 'busca'
    empresas = [
        'VVAR3',
        'PETR3',
        'ITSA4',
        'BRFS3',
        'IOBR3',
        'SQIA3',
        'VALE3',
        'LOGG3',
        'POMO4',
        'SAPR11',
        'NGRD3',
        'MOSI3',
   ]

    tabelas = [
        'Balanço Patrimonial Ativo',
        'Balanço Patrimonial Passivo',
        'Demonstração do Resultado',
        'Demonstração das Mutações do Patrimônio Líquido',
    ]

    def __init__(self):
        # Configuração do WebDriver PhantomJS - headless

        # service_args = [
        #     '--proxy = 187.94.211.54:3128',
        #     '--proxy-type=socks5',
        #     '--proxy-auth=username:password',
        # ]

        self.driver = webdriver.PhantomJS(executable_path=os.path.join(os.getcwd(), 'phantomjs-2.1.1-windows', 'bin', 'phantomjs'))
        self.driver.set_window_size(1024, 768)
        # self.driver = webdriver.Firefox()


    def start_requests(self):
        # Realiza, para cada empresa, uma busca no site b3.com.br
        for empresa in self.empresas:
            self.logger.info(f'Fazendo busca pela empresa de código: {empresa}')
            url = f'http://bvmf.bmfbovespa.com.br/cias-listadas/empresas-listadas/BuscaEmpresaListada.aspx?Nome={empresa}'

            yield scrapy.Request(url, callback=self.parse, cb_kwargs=dict(empresa=empresa))

    def parse(self, response, empresa):
        # Procura o código Cvm necessário para request na 
        # página da empresa no site bmfbovespa.com.br
        codigoCvm = response.xpath(
            "//tr[@class='GridRow_SiteBmfBovespa GridBovespaItemStyle']/td/a/@href").get()
        codigoCvm = codigoCvm.split('=')[-1]
        
        url = 'http://bvmf.bmfbovespa.com.br/cias-listadas/empresas-listadas/ResumoDemonstrativosFinanceiros.aspx?codigoCvm='+codigoCvm

        yield scrapy.Request(url, callback=self.parse_empresa, cb_kwargs=dict(empresa=empresa))

    def parse_empresa(self, response, empresa):
        url_relatorio = response.xpath(
            "//a[@id='ctl00_contentPlaceHolderConteudo_rptDocumentosDFP_ctl00_lnkDocumento']/@href").get()
        url_relatorio = url_relatorio.split("'")[-2]

        self.logger.info(f'Incializando WebDriver na página do relatório anual: {url_relatorio}...')
        self.driver.get(url_relatorio)

        # Dentro da página do relatório anual busca as tabelas procuradas
        dados = self.parse_relatorio_anual()
        yield Item(dados=dados, empresa=empresa)
    
    def parse_relatorio_anual(self):
        dados = {}
        wait = WebDriverWait(self.driver, 20)
        for nome_tabela in self.tabelas:
            # Espera carregamento do campo de seleção
            wait.until(EC.presence_of_element_located(
                (By.ID, 'cmbQuadro')))
            time.sleep(5)

            seletor_tabela = Select(
                self.driver.find_element_by_id("cmbQuadro"))

            self.logger.info(f'Visitando tabela {nome_tabela}...')
            seletor_tabela.select_by_visible_text(nome_tabela)

            # Espera carregamento da tabela
            wait.until(EC.presence_of_element_located(
                (By.XPATH, '//iframe[@id="iFrameFormulariosFilho"]')))
            time.sleep(1)

            # Busca o iframe (responsável pela tabela) na página
            iframe_match = re.search(
                r"(?<=window\.frames\[0\]\.location=').*?(?=';)", self.driver.page_source)

            iframe = f'https://www.rad.cvm.gov.br/ENETCONSULTA/{iframe_match[0]}'
            
            self.driver.get(iframe)
            self.driver.implicitly_wait(1)

            tabela = self.parse_iframe()

            dados[nome_tabela] = tabela
            self.driver.back()

        return dados

    def parse_iframe(self):
        tabela = []
        selector = scrapy.Selector(
            text=self.driver.page_source, type="html")
        linhas = selector.xpath('//tbody/tr')
        for line in linhas:
            l = line.xpath('.//td/text()').getall()
            l = [x.replace('\xa0', '') for x in l]
            tabela.append(l)

        return tabela


    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        # Whatever is here will run when the spider is done.
        self.driver.close()
