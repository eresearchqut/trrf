Feature: Patient Registration
  As the owner of TRRF
  I want patients and users to be able to self service their registration and authentication needs
  To minimise support requirements and maximise usability of the registry

  Background:
    Given export "ang.zip"
    Given a registry named "angelman" with code "ang"

  Scenario: Registration closed
    Given the registry is closed to registrations
    When I go to the "registration" page
    Then I should see "Sorry, but registration is closed at the moment."

  Scenario: Registration open
    Given the registry is open to registrations
    Given I am expecting to receive email
    When I go to the "registration" page
    Then I should see "Trial Ready Registry Framework - Patient Registration"

    # Patient self registers
    When I try to register as a user called "Bob Smith" using the email address "bob.smith@example.com" and the password "End2EndTest!s"
    Then I should see "Thank you for registration."
    And I have received an email:
      | To | From | Subject |
      | ['bob.smith@example.com'] | no-reply@registryframework.net | Welcome to the registry |

    # Patient activates their membership
    When I visit the provided link to activate my account
    Then I should see "Please activate your account."

    # Patient clicks the link to login
    When I press the "Activate my account" button
    Then I should be on the login page
    And I should see "You have successfully activated your account."

    # Patient uses their registered credentials to login
    When I login with username "bob.smith@example.com" and password "End2EndTest!s"
    Then I am logged in successfully