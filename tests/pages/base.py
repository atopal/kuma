from functools import wraps
import pytest
import re

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.action_chains import ActionChains

from pypom import Page, Region


def wait_for_window(fn):
    """
    Wait for the tab or window opened by the action.

    Firefox will sometimes return from click methods before the tab
    or window is fully opened. Chrome waits for the new window.
    """
    @wraps(fn)
    def with_wait_for_window(self=None, *args, **kwargs):
        page = self.page
        window_count = len(page.selenium.window_handles)
        fn(self, *args, **kwargs)
        self.wait.until(lambda s: len(s.window_handles) > window_count)

    return with_wait_for_window


class BasePage(Page):

    URL_TEMPLATE = '/{locale}'
    MM_BANNER_TEXT = 'MDN is currently in read-only maintenance mode.'
    MM_BANNER_SELECTOR = 'div.maintenance-mode-notice bdi'

    def __init__(self, selenium, base_url, locale='en-US', **url_kwargs):
        super(BasePage, self).__init__(selenium, base_url, locale=locale, **url_kwargs)

    def wait_for_page_to_load(self):
        self.wait.until(lambda s: self.seed_url in s.current_url)
        el = self.find_element(By.TAG_NAME, 'html')
        self.wait.until(lambda s: el.get_attribute('data-ffo-opensans'))
        return self

    @property
    def header(self):
        return self.Header(self)

    @property
    def footer(self):
        return self.Footer(self)

    @property
    def is_maintenance_mode_banner_displayed(self):
        mmb = self.find_element(By.CSS_SELECTOR, self.MM_BANNER_SELECTOR)
        return mmb.is_displayed() and (self.MM_BANNER_TEXT in mmb.text)

    def disable_survey_popup(self):
        """Avoid the task completion survey popup for 5 minutes."""
        self.selenium.execute_script(
            "localStorage.setItem('taskTracker', Date.now() + (1000*60*5));")
        self.selenium.refresh()
        self.wait_for_page_to_load()

    def enable_survey_popup(self):
        """Allow the task completion survey popup."""
        self.selenium.execute_script(
            "localStorage.removeItem('taskTracker');")
        self.selenium.refresh()
        self.wait_for_page_to_load()

    class Header(Region):
        report_content_form_url = 'https://bugzilla.mozilla.org/form.doc'
        report_bug_form_url = 'https://bugzilla.mozilla.org/form.mdn'
        # locators
        SIGNIN_SELECTOR = '#nav-sec .login-link'

        _root_locator = (By.ID, 'main-header')
        _menu_top_links = (By.CSS_SELECTOR, '#main-nav > ul > li > a[href]')
        _logo_locator = (By.CSS_SELECTOR, 'a.logo')
        _tech_submenu_trigger_locator = (By.XPATH,
                                         'id(\'nav-tech-submenu\')/..')
        _tech_submenu_locator = (By.ID, 'nav-tech-submenu')
        _tech_submenu_link_locator = (By.CSS_SELECTOR, '#nav-tech-submenu a')
        _feedback_link_locator = (By.XPATH, 'id(\'nav-contact-submenu\')/../a')
        _feedback_submenu_trigger_locator = (By.XPATH,
                                             'id(\'nav-contact-submenu\')/..')
        _feedback_submenu_locator = (By.ID, 'nav-contact-submenu')
        _report_content_locator = (By.CSS_SELECTOR,
                                   'a[href^="' + report_content_form_url + '"]')
        _report_bug_locator = (By.CSS_SELECTOR,
                               'a[href^="' + report_bug_form_url + '"]')
        _search_field_locator = (By.ID, 'main-q')
        _search_trigger_locator = (By.CSS_SELECTOR, 'span.search-trigger')

        # is displayed?
        @property
        def is_displayed(self):
            return self.root.is_displayed()

        @property
        def signin_link(self):
            return self.find_element(By.CSS_SELECTOR, self.SIGNIN_SELECTOR)

        def trigger_signin(self):
            self.signin_link.click()

        # is the sign-in button displayed?
        @property
        def is_signin_displayed(self):
            return self.signin_link.is_displayed()

        # top level links from navigation menu
        @property
        def menu_top_links_list(self):
            return self.find_element(*self._menu_top_links)

        # technology submenu (HTML, CSS, JavaScript)
        @property
        def is_tech_submenu_trigger_displayed(self):
            submenu_trigger = self.find_element(*self._tech_submenu_trigger_locator)
            return submenu_trigger.is_displayed()

        @property
        def is_tech_submenu_displayed(self):
            submenu = self.find_element(*self._tech_submenu_locator)
            return submenu.is_displayed()

        def show_submenu(self, menu_element, revealed_element,
                         off_element=None):
            """Hover over a menu element that reveals another element.

            For Chrome and local Firefox, it is sufficent to move to the
            element to get a hover.

            For the Remote driver with Firefox, it is more reliable if the
            mouse is first moved off-element, and then on-element. It still
            occasionally fails in some contexts, such as the homepage.
            (geckodriver 0.19.1, Selenium 3.8.1, Firefox 57).
            """
            if off_element is None:
                # Use the logo as the element that isn't the hover menu
                off_element = self.find_element(*self._logo_locator)
            hover = (ActionChains(self.selenium)
                     .move_to_element(off_element)
                     .move_to_element(menu_element))
            hover.perform()
            try:
                self.wait.until(lambda s: revealed_element.is_displayed())
            except TimeoutException:
                if self.selenium._is_remote and self.selenium.name == 'firefox':
                    pytest.xfail("Known issue with hover"
                                 " (Selenium 3 w/ Remote Firefox)")
                raise

        def show_tech_submenu(self):
            submenu_trigger = self.find_element(*self._tech_submenu_trigger_locator)
            submenu = self.find_element(*self._tech_submenu_locator)
            self.show_submenu(submenu_trigger, submenu)

        # feedback submenu
        @property
        def is_feedback_submenu_trigger_displayed(self):
            submenu_trigger = self.find_element(*self._feedback_submenu_trigger_locator)
            return submenu_trigger.is_displayed()

        @property
        def is_feedback_submenu_displayed(self):
            submenu = self.find_element(*self._feedback_submenu_locator)
            return submenu.is_displayed()

        @property
        def is_report_content_link_displayed(self):
            report_content_link = self.find_element(*self._report_content_locator)
            return report_content_link.is_displayed()

        @property
        def is_report_bug_link_displayed(self):
            report_bug_link = self.find_element(*self._report_bug_locator)
            return report_bug_link.is_displayed()

        def show_feedback_submenu(self):
            submenu_trigger = self.find_element(*self._feedback_submenu_trigger_locator)
            submenu = self.find_element(*self._feedback_submenu_locator)
            self.show_submenu(submenu_trigger, submenu)

        def open_feedback(self, locale=None):
            self.find_element(*self._feedback_link_locator).click()
            # import needs to be here to avoid circular reference
            from pages.article import ArticlePage
            url_kwargs = dict(locale=locale) if locale else dict()
            feedback_page = ArticlePage(self.selenium,
                                        self.page.base_url,
                                        **url_kwargs)
            feedback_page.URL_TEMPLATE = '/{locale}/docs/MDN/Feedback'
            return feedback_page.wait_for_page_to_load()

        def localized_feedback_path(self, locale):
            link = self.find_element(*self._feedback_link_locator)
            href = link.get_attribute('href')
            # base url may or may not be part of string
            path = re.sub(self.page.base_url, '', href)
            # if base url was not part of string there's a leading / to remove
            path = re.sub(r'^/', '', path)
            # remove locale and following /
            path = re.sub(r'^' + locale + '\/', '', path)
            return path

        @wait_for_window
        def open_report_content(self):
            self.find_element(*self._report_content_locator).click()

        def is_report_content_url_expected(self, selenium, article_url):
            current_url = selenium.current_url
            report_url = self.report_content_form_url
            # compare
            url_matches = report_url in current_url
            # TODO check url contains article url in query variable
            return url_matches

        @wait_for_window
        def open_report_bug(self):
            self.find_element(*self._report_bug_locator).click()

        @property
        def search_field_width(self):
            search_field = self.find_element(*self._search_field_locator)
            return search_field.size['width']

        def search_field_focus(self):
            plaform_submenu_trigger = self.find_element(*self._tech_submenu_trigger_locator)
            search_field = self.find_element(*self._search_trigger_locator)
            focus = ActionChains(self.selenium).move_to_element(search_field).click()
            focus.perform()
            # this can be a bit flaky sometimes
            self.wait.until(lambda s: not plaform_submenu_trigger.is_displayed())

        def search_for_term(self, term):
            search_field = self.find_element(*self._search_field_locator)
            search_field.send_keys('css', Keys.ENTER)
            from pages.search import SearchPage
            return SearchPage(self.selenium, self.page.base_url, term=term).wait_for_page_to_load()

    class Footer(Region):
        privacy_url = 'https://www.mozilla.org/privacy/websites/'
        copyright_url = '/docs/MDN/About#Copyrights_and_licenses'
        # locators
        _root_locator = (By.CSS_SELECTOR, 'body > footer')
        _language_locator = (By.ID, 'language')
        _privacy_locator = (By.CSS_SELECTOR, 'a[href^="' + privacy_url + '"]')
        _license_locator = (By.CSS_SELECTOR, 'a[href$="' + copyright_url + '"]')

        # is displayed?
        @property
        def is_displayed(self):
            return self.root.is_displayed()

        # language select is displayed
        @property
        def is_select_language_displayed(self):
            return self.find_element(*self._language_locator).is_displayed()

        # check language selected locale
        @property
        def language_value(self):
            # get language selected
            language_select = self.find_element(*self._language_locator)
            selected_option = language_select.find_element(By.CSS_SELECTOR, 'option[selected]')
            selected_language = selected_option.get_attribute('value')
            return selected_language

        def select_language(self, value):
            language_select = self.find_element(*self._language_locator)
            Select(language_select).select_by_value(value)
            self.wait.until(lambda s: '/{0}/'.format(value) in s.current_url)

        # privacy link is displayed
        @property
        def is_privacy_displayed(self):
            return self.find_element(*self._privacy_locator).is_displayed()

        # license link is displayed
        @property
        def is_license_displayed(self):
            return self.find_element(*self._license_locator).is_displayed()
