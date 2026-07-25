package com.example.stepdefs;

import com.example.pages.LoginPage;
import io.cucumber.java.en.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;

public class LoginSteps {
    WebDriver driver;
    LoginPage loginPage;

    @Given("I am on the login page")
    public void i_am_on_the_login_page() {
        driver = new ChromeDriver();
        driver.get("https://example.com/login");
        loginPage = new LoginPage(driver);
    }

    @When("I enter username {string} and password {string}")
    public void i_enter_credentiallsis(String username, String password2) {
        loginPage.enterUsername(username);
        loginPage.enterPassword(password2);
    }

    @And("I click login")
    public void i_click_login() {
        loginPage.clickLogin();
    }

    @Then("I should be redirected to the dashboard")
    public void i_should_be_redirected() {
        // Add assertion here
        driver.quit();
    }
}
