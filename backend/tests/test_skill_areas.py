from moneyplease.skill_areas import AREAS, SKILL_AREA, area_of, find_skill


def test_known_areas():
    assert area_of("Spring Boot") == "backend"
    assert area_of("React 19") == "frontend"
    assert area_of("Kubernetes") == "cloud"
    assert area_of("Snowflake") == "datos"
    assert area_of("JUnit") == "testing"
    assert area_of("Inglés") == "idiomas"


def test_unknown_is_otros():
    assert area_of("Cobol") == "otros"
    assert area_of("") == "otros"


def test_dictionary_size_and_areas():
    assert len(SKILL_AREA) >= 60
    assert set(SKILL_AREA.values()) <= set(AREAS)


def test_find_skill_longest_match():
    assert find_skill("Pide experiencia con Spring Boot y Java") == "spring boot"
    assert find_skill("Pide Kubernetes") == "kubernetes"


def test_find_skill_none():
    assert find_skill("") is None
    assert find_skill("Experiencia en ventas") is None


def test_single_letter_skills_not_matched():
    assert find_skill("Conocimiento de C++ y C") is None
    assert "c" not in SKILL_AREA


def test_skills_in_con_simbolos():
    from moneyplease.skill_areas import skills_in
    assert skills_in("Buscamos C# y .NET, ideal C++ y Java") == {"c#", ".net", "c++", "java"}


def test_skills_in_no_confunde_java_con_javascript():
    from moneyplease.skill_areas import skills_in
    assert skills_in("JavaScript dev") == {"javascript"}


def test_skills_in_prefiere_la_mas_larga():
    from moneyplease.skill_areas import skills_in
    assert skills_in("Spring Boot y ASP.NET") == {"spring boot"}


def test_area_de_habilidades_con_simbolos():
    from moneyplease.skill_areas import area_of
    assert area_of("C#") == "backend" and area_of(".NET") == "backend"
