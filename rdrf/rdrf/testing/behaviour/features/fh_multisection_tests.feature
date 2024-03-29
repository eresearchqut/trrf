Feature: User operates on multisection items.
  A user can:
  Add items (single section data) to a multisection and delete an item
  by checking the "Mark for Deletion" checkbox and saving.

  Background:
    Given export "fh.zip"
    Given a registry named "FH Registry"

  Scenario: Add multiple items to a multisection.
    When I am logged in as curator
    And I click "Menu"
    And I click "Patient List (FH Registry)"
    When I click Module "Main/Imaging" for patient "SMITH John" on patientlisting
    Then location is "Main/Imaging"

    # Enter first item
    And I expand the "Carotid Ultrasonography" section
    And I enter value "01-01-2017" for form "Imaging" multisection "Carotid Ultrasonography" cde "Date" in item 1
    And I enter value "4.0" for form "Imaging" multisection "Carotid Ultrasonography" cde "Result (right)" in item 1
    And I enter value "item 1" for form "Imaging" multisection "Carotid Ultrasonography" cde "Result" in item 1
    When I upload file "/app/license.txt" for multisection "Carotid Ultrasonography" cde "Report" in item 1
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    And I expand the "Carotid Ultrasonography" section
    Then I should be able to download "license.txt"

    # Enter second item
    When I click the add button for multisection "Carotid Ultrasonography"
    And I enter value "02-01-2017" for form "Imaging" multisection "Carotid Ultrasonography" cde "Date" in item 2
    And I enter value "3.0" for form "Imaging" multisection "Carotid Ultrasonography" cde "Result (right)" in item 2
    And I enter value "item 2" for form "Imaging" multisection "Carotid Ultrasonography" cde "Result" in item 2
    When I upload file "/app/authors.txt" for multisection "Carotid Ultrasonography" cde "Report" in item 2
    And I click the "Save" button
    Then I should see "Patient John SMITH saved successfully"
    And I expand the "Carotid Ultrasonography" section
    And I should be able to download "license.txt"
    And I should be able to download "authors.txt"

    # delete the first item of the multisection
    When I mark multisection "Carotid Ultrasonography" item 1 for deletion
    And I click the "Save" button
    And I expand the "Carotid Ultrasonography" section
    Then I should not be able to download "license.txt"
    And I should be able to download "authors.txt"

    # check some values - we deleted the 1st item so what remains is the original 2nd item
    And the value of multisection "Carotid Ultrasonography" cde "Date" item 1 is "02-01-2017"
    And the value of multisection "Carotid Ultrasonography" cde "Result (right)" item 1 is "3.0"
