import xlsxwriter
import os

from itemadapter import ItemAdapter


class RelatoriosEstruturadosPipeline:
    def process_item(self, item, spider):

        dados = item['dados']
        empresa = item['empresa']
        os.makedirs(os.path.join(os.getcwd(), 'data', empresa), exist_ok=True)
        for tabela in list(dados.keys()):
            with xlsxwriter.Workbook(f"{os.path.join('data', empresa, tabela)}.xlsx") as workbook:
                worksheet = workbook.add_worksheet()

                for row_num, data in enumerate(dados[tabela]):
                    worksheet.write_row(row_num, 0, data)
        return item
