Feature: Password management
  As a user of TRRF
  I want to be able to help myself when I forget my password
  So that I can quickly gain access to my account without needing to contact support

  Background:
    Given export "ang.zip"
    Given a registry named "angelman" with code "ang"
    Given I am expecting to receive email

  Scenario: Forgot my password
    Given a user "John Smith" with username "patient.test@example.com" and password "Or1g1n4l Pa$$word"
    When I go to the "login" page
    And click "Trouble signing in?"
    Then I should see "Forgotten your password?"

    # Request a password reset
    When I request to reset my password for "patient.test@example.com"
    Then I should see "We've emailed you instructions for setting your password"
    And I have received an email:
      | To | From | Subject |
      | ['patient.test@example.com'] | no-reply@registryframework.net | Password reset on TRRF-Aloe |

    # Reset password using the provided link
    When I visit the provided link to reset my password
    Then I should see "Please enter your new password twice so we can verify you typed it in correctly."

    When I set my new password to "n3w Pa$$word"
    Then I should see "Your password has been set. You may go ahead and log in now."

    When I click "Log in"
    And I login with username "patient.test@example.com" and password "Or1g1n4l Pa$$word"
    Then I should see "Please enter a correct username and password."

    When I login with username "patient.test@example.com" and password "n3w Pa$$word"
    Then I am logged in successfully