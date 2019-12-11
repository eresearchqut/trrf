from enum import Enum


class SystemRoles(Enum):
    CIC_DEV = 'CIC_DEV'
    CIC_PROMS = 'CIC_PROMS'
    CIC_CLINICAL = 'CIC_CLINICAL'
    NORMAL = 'NORMAL'
    NORMAL_NO_PROMS = 'NORMAL_NO_PROMS'

    @property
    def is_normal_no_proms(self):
        return self == SystemRoles.NORMAL_NO_PROMS

    @property
    def is_normal(self):
        return self == SystemRoles.NORMAL

    @property
    def is_cic_dev(self):
        return self == SystemRoles.CIC_DEV

    @property
    def is_cic_clinical(self):
        return self == SystemRoles.CIC_CLINICAL

    @property
    def is_cic_proms(self):
        return self == SystemRoles.CIC_PROMS

    @property
    def is_cic_non_proms(self):
        return self.is_cic_dev or self.is_cic_clinical

    @property
    def is_cic_role(self):
        return self in (SystemRoles.CIC_DEV, SystemRoles.CIC_PROMS, SystemRoles.CIC_CLINICAL)
