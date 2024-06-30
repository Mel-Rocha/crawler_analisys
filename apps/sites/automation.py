import time
import logging

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from tenacity import stop_after_attempt, retry
from selenium.common import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from apps.core.base_automation import CoreAutomation

logging.basicConfig(level=logging.INFO)


class GeneralAutomation(CoreAutomation):
    def __init__(self, base_url, item_div_class, img_xpath_template, next_page_xpath=None):
        super().__init__()
        self.base_url = base_url
        self.item_div_class = item_div_class
        self.img_xpath_template = img_xpath_template
        self.next_page_xpath = next_page_xpath
        self.old_len = 0
        self.metrics = []
        self.automation_failure_analysis = []

    @staticmethod
    def automation_validation(page_number, num_div_elements, current_url_all, old_len):
        num_urls_extracted = len(current_url_all) - old_len
        print(f"Número da Página: {page_number}")
        print(f"Quantidade de Itens: {num_div_elements}")
        print(f"Quantidade de URLs extraídas: {num_urls_extracted}")

        validation_dict = {
            'page_number': page_number,
            'ads_found': num_div_elements,
            'extracted_urls': num_urls_extracted
        }

        return validation_dict

    @retry(stop=stop_after_attempt(3))
    def access_url(self, url):
        self.driver.get(url)

    def extract_urls(self):
        current_url_all = []
        page_number = 0

        try:
            while True:
                url_page_list = f"{self.base_url}?page={page_number}"
                self.access_url(url_page_list)
                time.sleep(2)

                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

                all_product = soup.find('div', class_=self.item_div_class)
                if not all_product:
                    break

                div_elements = all_product.find_all('div', class_='item-veiculo')
                num_div_elements = len(div_elements)
                if num_div_elements == 0:
                    break

                if div_elements:
                    self.old_len = len(current_url_all)

                    for i, img in enumerate(div_elements, start=0):
                        img_xpath = self.img_xpath_template.format(i)
                        logging.info(img_xpath)

                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.visibility_of_element_located((By.XPATH, img_xpath)))
                            img_element = self.driver.find_element(By.XPATH, img_xpath)
                            logging.info(self.driver.current_url)
                            self.driver.execute_script("arguments[0].click();", img_element)
                            time.sleep(3)
                            current_url_all.append(self.driver.current_url)
                            logging.info(current_url_all)
                        except TimeoutException as e:
                            print(f"Erro ao clicar na imagem: Tempo de execução limite {e}")
                            logging.error(
                                "O elemento foi encontrado, mas não se tornou visivel dentro do tempo limite.")
                            self.automation_failure_analysis.append(img_xpath)
                            continue
                        except NoSuchElementException as e:
                            print(f"Erro ao clicar na imagem: Imagem não encontrada {e}.")
                            logging.error("O elemento não foi encontrado.")
                            self.automation_failure_analysis.append(img_xpath)
                            continue

                        self.driver.back()
                        time.sleep(2)

                metrics = self.automation_validation(page_number, num_div_elements, current_url_all, self.old_len)
                self.metrics.append(metrics)

                page_number += 1

                # Optional: If there's a specific "next page" element to click
                if self.next_page_xpath:
                    try:
                        next_page_element = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, self.next_page_xpath))
                        )
                        next_page_element.click()
                        time.sleep(2)
                    except (TimeoutException, NoSuchElementException):
                        break
        finally:
            super().stop_driver()
            print(self.metrics)
            return current_url_all, self.metrics, self.automation_failure_analysis


if __name__ == "__main__":
    base_url = 'https://www.caminhoesecarretas.com.br/venda/pa%20carregadeira/23'
    item_div_class = ['productList', 'product-load-more']
    img_xpath_template = '//*[@id="ContentPlaceHolder1_lvVeiculo_lnkVeiculo_{0}"]/img'

    automation = GeneralAutomation(base_url, item_div_class, img_xpath_template)
    urls, metrics, failures = automation.extract_urls()
    print(urls, metrics, failures)
