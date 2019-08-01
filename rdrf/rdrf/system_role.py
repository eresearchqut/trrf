from enum import Enum


class SystemRoles(Enum):
    CIC_DEV = 'CIC_DEV'
    CIC_PROMS = 'CIC_PROMS'
    CIC_CLINICAL = 'CIC_CLINICAL'
    NORMAL = 'NORMAL'

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
        return not self.is_normal
