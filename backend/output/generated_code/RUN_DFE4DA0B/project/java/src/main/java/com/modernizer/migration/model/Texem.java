package com.modernizer.migration.model;

/**
 * Generated model from COBOL copybook TEXEM.cpy.
 * Fields are derived from COBOL PIC clauses and locked symbol mappings.
 */
public class Texem {
    private String firstName;
    private String lastName;
    private String tmsCrea;

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }
    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }
    public String getTmsCrea() {
        return tmsCrea;
    }

    public void setTmsCrea(String tmsCrea) {
        this.tmsCrea = tmsCrea;
    }
}
