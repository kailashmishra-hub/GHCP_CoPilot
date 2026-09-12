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
