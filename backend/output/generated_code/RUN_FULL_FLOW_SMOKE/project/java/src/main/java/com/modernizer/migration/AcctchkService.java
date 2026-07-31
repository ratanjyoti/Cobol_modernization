package com.modernizer.migration;

import jakarta.enterprise.context.ApplicationScoped;
import java.math.BigDecimal;

/**
 * Generated from ACCTCHK.CBL.
 * Business intent is sourced from verified business rules and COBOL evidence.
 */
@ApplicationScoped
public class AcctchkService {
    // Business rule: If customer balance is negative, the account must be marked as overdraft.

    /**
     * If customer balance is negative, the account must be marked as overdraft.
     *
     * @param customerBalance current customer/account balance
     * @return true when the account is in overdraft
     */
    public boolean evaluateOverdraft(BigDecimal customerBalance) {
        if (customerBalance == null) {
            throw new IllegalArgumentException("customerBalance is required");
        }
        return customerBalance.compareTo(BigDecimal.ZERO) < 0;
    }
}
