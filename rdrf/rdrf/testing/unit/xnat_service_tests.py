from django.test import TestCase

from rdrf.integration.xnat_service import xnat_experiments_scans


class XnatServiceTest(TestCase):
    def test_xnat_experiments_scans(self):
        mock_project_id = "PT-1"
        mock_subject_id = "patient1"
        results = xnat_experiments_scans(mock_project_id, mock_subject_id)

        self.assertEqual(
            results,
            [
                {
                    "date": "2023-01-16 03:04:55.16",
                    "id": "XNAT_E00001",
                    "label": "patient1_ID",
                    "URI": "/data/experiments/XNAT_E00001",
                    "scans": [
                        {
                            "id": "6",
                            "type": "CT_Thorax_Abdomen",
                            "series_description": "CT_Thorax_Abdomen",
                            "URI": "/data/experiments/XNAT_E00001/scans/6",
                        }
                    ],
                }
            ],
        )
