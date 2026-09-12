Feature: Search functionality

  @search_valid
  Scenario: Search for a valid product
    Given I am on the home page
    When I search for "Laptop"
    Then I should see results related to "Laptop"

  @search_invalid
  Scenario: Search for an invalid product
    Given I am on the home page
    When I search for "NonExistingProduct"
    Then I should see a "No results found" message

  @ui_utils
  Scenario: Use BasePage utilities to search and interact
    Given I am on the home page
    When I scroll to the search section
    And I select "Electronics" from category dropdown
    And I search for "Smartphone"
    Then I should see results related to "Smartphone"

  @wait_page_load
  Scenario: Wait for full page load
    Given I navigate to "/slow-page"
    When I wait for the page to load within 10 seconds
    Then the page should be fully loaded

  @wait_for_text
  Scenario: Wait for text to appear on the page
    Given I am on the home page
    When I wait for text "Welcome" to appear within 5 seconds
    Then I should see "Welcome" on the page

  @screenshot
  Scenario: Capture screenshot of the page
    Given I am on the home page
    When I take a screenshot
    Then a screenshot should be available for debugging

  @current_url
  Scenario: Verify current URL after navigation
    Given I navigate to "/dashboard"
    Then the current url should contain "/dashboard"

  @refresh
  Scenario: Refresh page and verify content reload
    Given I am on the home page
    When I refresh the page
    Then the page content should be refreshed

  @wait_invisibility
  Scenario: Wait for loading spinner to disappear
    Given I am on the home page
    When I wait for the loading spinner to disappear within 10 seconds
    Then the loading spinner should not be visible

  @get_size
  Scenario: Verify number of search results is greater than zero
    Given I am on the products page
    When I get the number of product results
    Then the number of results should be greater than 0
