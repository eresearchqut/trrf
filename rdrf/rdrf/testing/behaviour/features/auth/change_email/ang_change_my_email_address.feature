Feature: Change my email address
  As a user of TRRF
  I want to be able to self-service an email address change
  So that I can keep my details current without requiring additional support to do so.

  Background:
    Given export "ang.zip"
    Given a registry named "angelman" with code "ang"
    Given I am expecting to receive email

  Scenario: Change my email
    Given a user "John Smith" with username "john.smith@test.com" and password "MyPas!word"
    And I log in as "john.smith@test.com" with "MyPas!word" password

    # Initiate an email change request, invalid
    When I choose "Change Email Address" from the "user" menu
    Then my current email is displayed "john.smith@test.com"
    And I enter a new email address "john2_smith@example.com"
    And I confirm the new email address as "john2_smith@example.com"
    And I enter a password "Wrong Password!"
    And submit the form
    Then I get an error "Your current password is incorrect"

    # Initiate an email change request, valid
    When I enter a password "MyPas!word"
    And submit the form
    Then my "Current Email Change Request" is displayed, with the following details:
      | Requested email address | Status |
      | john2_smith@example.com | PENDING |
    And I have received an email:
      | To | From | Subject |
      | ['john2_smith@example.com'] | no-reply@registryframework.net | New Email Address Activation |

    # Attempt to log in with new email before it's activated
    When I logout
    And I login with username "john2.smith@test.com" and password "MyPas!word"
    Then I should see "Please enter a correct username and password."
    When I login with username "john.smith@test.com" and password "MyPas!word"
    Then I am logged in successfully

    # Activate new email
    When I logout
    And  I visit the provided link to activate my account
    Then I should see "You have successfully activated your account."

    # Attempt to log in with old email
    When I click "login page"
    And  I login with username "john.smith@test.com" and password "MyPas!word"
    Then I should see "Please enter a correct username and password."
    When I login with username "john2_smith@example.com" and password "MyPas!word"
    Then I am logged in successfully
