Feature: FH Family Linkage Page
  As a user of FH
  I want to be able to view the families of patients
  In order to do cascade screening.

  Background:
    Given site has loaded export "fh_with_data.zip"
    
  Scenario: User can visit Family Linkage Page
    Given I login as curator
    When I click "SMITH, John" on patientlisting
    When I click "Family Linkage" in sidebar
    Then location is "Family Linkage"
    
