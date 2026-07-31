package com.modernizer.migration.model;

import java.math.BigDecimal;

/**
 * Generated model from COBOL copybook TEXE2.cpy.
 * Fields are derived from COBOL PIC clauses and locked symbol mappings.
 */
public class Texe2 {
    private String firstName;
    private String lastName;
    private BigDecimal wallet;
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
    public BigDecimal getWallet() {
        return wallet;
    }

    public void setWallet(BigDecimal wallet) {
        this.wallet = wallet;
    }
    public String getTmsCrea() {
        return tmsCrea;
    }

    public void setTmsCrea(String tmsCrea) {
        this.tmsCrea = tmsCrea;
    }
}
