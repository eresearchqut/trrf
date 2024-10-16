Feature: Edit diagnosis for a patient
  As a RDRF registry owner
  I want curators to edit diagnosis for patients

  Background:
    Given export "dd.zip"
    Given a registry named "Demyelinating Diseases Registry"
    And a patient named "ABBOTT Abigail"

  Scenario: Curator navigates to diagnosis
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List (Demyelinating Diseases Registry)"
    When I click "ABBOTT Abigail" on patientlisting
    When I click "Diagnosis" in sidebar
    Then the progress indicator should be "0%"

  Scenario: Curator edits diagnosis
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List (Demyelinating Diseases Registry)"
    When I click "ABBOTT Abigail" on patientlisting
    When I click "Diagnosis" in sidebar
    Then the progress indicator should be "0%"
    And I expand the "Status" section
    And I select "PP (Primary progressive)" from "Condition"
    And I select "DD Affected Status 2" from "Affected Status"
    And I select "Family" from "First Suspected By"
    And I fill in "Date of Diagnosis" with "1-2-1991"
    And I check "Family Consent"
    And I press the "Save" button
    Then I should see "Patient Abigail ABBOTT saved successfully"

  Scenario: Curator edits diagnosis, leave and returns
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List (Demyelinating Diseases Registry)"
    When I click "ABBOTT Abigail" on patientlisting
    When I click "Diagnosis" in sidebar
    Then the progress indicator should be "0%"
    And I expand the "Status" section
    And I select "PP (Primary progressive)" from "Condition"
    And I select "DD Affected Status 2" from "Affected Status"
    And I select "Family" from "First Suspected By"
    And I fill in "Date of Diagnosis" with "1-2-1991"
    And I check "Family Consent"
    And I press the "Save" button
    Then I should see "Patient Abigail ABBOTT saved successfully"
    When I navigate away then back
    And I expand the "Status" section
    Then the progress indicator should be "12%"
    Then option "PP (Primary progressive)" from "Condition" should be selected
    And option "DD Affected Status 2" from "Affected Status" should be selected
    And option "Family" from "First Suspected By" should be selected
    And value of "Date of Diagnosis" should be "01-02-1991"
    And the "Family Consent" checkbox should be checked
    And value of "Age in years at clinical diagnosis" should be "57"

  Scenario: Curator edits multisection
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List (Demyelinating Diseases Registry)"
    When I click "ABBOTT Abigail" on patientlisting
    When I click "Diagnosis" in sidebar
    Then the progress indicator should be "0%"
    And I expand the "Medical History Record" section
    And I fill "Date" with "1-2-1991" in MultiSection "MedicalHistoryRecord" index "0"
    And I press the "Save" button
    Then I should see "Patient Abigail ABBOTT saved successfully"

    # TODO
    #  add multisection, edit, save, leave, return, check
