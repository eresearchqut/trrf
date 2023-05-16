Feature: Longitudinal followup email notifications
  As a user of FH
  I want to get email notifications when I'm due to follow up on forms
  So that I can regularly add new data to the registry

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry" with code "fh"
    Given I am expecting to receive email
    Given I am logged in as curator

  Scenario: Receive a followup email
    Given the "Follow Up" form in patient "SMITH John" is filled out
    When 1 hour passes
    Then 0 emails are sent

    When 24 hours pass
    Then 1 email is sent
    And email 1 has 1 link
    And each link in email 1 loads successfully

    Then the mail is emptied

    When 48 hours pass
    Then no emails are sent


  Scenario: Receive a combined followup email
    Given the "Follow Up" form in patient "SMITH John" is filled out
    And the "Second Follow Up" form in patient "SMITH John" is filled out
    When 1 hour passes
    Then 0 emails are sent

    When 24 hours pass
    Then 1 email is sent
    And email 1 has 2 links
    And each link in email 1 loads successfully

    Then the mail is emptied

    When 48 hours pass
    Then no emails are sent


  Scenario: Receive emails only when subscribed
    Given the "Follow Up" form in patient "SMITH John" is filled out
    When 1 hour passes
    Then 0 emails are sent

    When 24 hours pass
    Then 1 email is sent

    Then the mail is emptied

    When the "Follow Up" form in patient "SMITH John" is filled out again
    And 48 hours pass
    Then 1 email is sent
    Then I unsubscribe in email 1

    Then the mail is emptied

    When the "Follow Up" form in patient "SMITH John" is filled out again
    And 72 hours pass
    Then 0 emails are sent
