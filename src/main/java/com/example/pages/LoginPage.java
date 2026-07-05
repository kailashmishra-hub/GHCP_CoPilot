package com.example.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class LoginPage extends BasePage {
    private By usernameField = By.id("username");
    private By passwordField = By.id("password");
    private By loginButton = By.id("login");

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void enterUsername(String username2) {
        System.out.println("Hello Hello");
        driver.findElement(usernameField).sendKeys(username2);
    }

    public void enterPassword(String password) {
        driver.findElement(passwordField).sendKeys(password);
    }

    public void clickLogin() {

        driver.findElement(loginButton).click();
    }
}
