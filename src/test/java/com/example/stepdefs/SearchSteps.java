package com.example.stepdefs;
import com.example.pages.LoginPage;
import com.example.pages.SearchPage;
import io.cucumber.java.en.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.junit.Assert;

public class SearchSteps {
    WebDriver driver;
    SearchPage searchPage;
    LoginPage loginPage;
    @Given("I am on the home page")

    public void i_am_on_the_home_page() {
        driver = new ChromeDriver();
        driver.get("https://example.com/home");
        searchPage = new SearchPage(driver);
        loginPage.enterPassword("password1");
    }

    @When("I search for {string}")
    public void i_search_for(String term) {
        searchPage.enterSearchTerm(term);
        searchPage.clickSearch();
    }

    @Then("I should see results related to {string}")
    public void i_should_see_results(String term) {
        Assert.assertTrue("Results are not displayed!", searchPage.isResultsDisplayed());
        driver.quit();
    }

    @Then("I should see a {string} message")
    public void i_should_see_a_message(String message) {
        Assert.assertTrue("No results are in the message not displayed!", searchPage.isNoResultsMessageDisplayed());
        driver.quit();
    }
}
