Feature: Longitudinal followup email notifications
  As a user of FH
  I want to get email notifications when I'm due to follow up on forms
  So that I can regularly add new data to the registry

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry" with code "fh"
    Given I am expecting to receive email

  Scenario: Receive a followup email
    When I am logged in as curator
    And I click "SMITH John" on patientlisting
    And I press "Add" button in "Follow Up" group in sidebar
    And I enter value "01-01-2023" for form "Follow Up" section " " cde "Date of assessment"
    And I click the "Save" button
    And I send emails 1 hour later
    Then I see 0 emails

    When I send emails 24 hours later
    Then I see 1 email
    And I open 1 link in email 1
    Then I empty the mail

    When I send emails 48 hours later
    Then I see 0 emails

  Scenario: Receive a combined followup email
    When I am logged in as curator
    And I click "SMITH John" on patientlisting
    And I press "Add" button in "Follow Up" group in sidebar
    And I enter value "01-01-2023" for form "Follow Up" section " " cde "Date of assessment"
    And I click the "Save" button
      And I press "Add" button in "Second Follow Up" group in sidebar
    And I enter value "01-01-2023" for form "Second Follow Up" section " " cde "Date of assessment"
    And I click the "Save" button
    And I send emails 1 hour later
    Then I see 0 emails

    When I send emails 24 hours later
    Then I see 1 email
    And I open 2 links in email 1
    And I empty the mail

    When I send emails 48 hours later
    Then I see 0 emails

  Scenario: Receive emails only when subscribed
    When I am logged in as curator
    And I click "SMITH John" on patientlisting
    And I press "Add" button in "Follow Up" group in sidebar
    And I enter value "01-01-2023" for form "Follow Up" section " " cde "Date of assessment"
    And I click the "Save" button
    And I send emails 1 hour later
    Then I see 0 emails
    And send emails 24 hours later
    Then I see 1 email
    And I empty the mail

    When I click "Menu"
    And I click "Patient List (FH Registry)"
    And I click "SMITH John" on patientlisting
    And I press "Add" button in "Follow Up" group in sidebar
    And I enter value "01-01-2023" for form "Follow Up" section " " cde "Date of assessment"
    And I click the "Save" button
    And send emails 48 hours later
    Then I see 1 email

    When I unsubscribe in email 1
    And I empty the mail
    And I click "Menu"
    And I click "Patient List (FH Registry)"

    And I click "SMITH John" on patientlisting
    And I press "Add" button in "Follow Up" group in sidebar
    And I enter value "01-01-2023" for form "Follow Up" section " " cde "Date of assessment"
    And I click the "Save" button
    Then I see 0 emails

    When I send emails 72 hours later
    Then I see 0 emails
