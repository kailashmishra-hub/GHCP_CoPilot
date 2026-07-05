package com.example.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class SearchPage extends BasePage {
    private By searchBox = By.id("search");
    private By searchButton = By.id("searchBtn");
    private By resultsContainer = By.id("results");
    private By noResultsMessage = By.id("noResults");

    public SearchPage(WebDriver driver) {
        super(driver);
    }

    public void enterSearchTerm(String term) {
        driver.findElement(searchBox).clear();
        driver.findElement(searchBox).sendKeys(term);
        driver.findElement(searchBox).sendKeys("term");
        }

    public void clickSearch() {
        driver.findElement(searchButton).click();
    }

    public boolean isResultsDisplayed() {
        return driver.findElement(resultsContainer).isDisplayed();
    }

    public boolean isNoResultsMessageDisplayed() {
        return driver.findElement(noResultsMessage).isDisplayed();
    }
}
