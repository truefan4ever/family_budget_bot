from decimal import Decimal
from itertools import groupby
from operator import attrgetter
from typing import Iterable, Optional

from analytics.messages import (
    CURRENCY_REPORT_TITLE_MESSAGE,
    INCOME_OTHER_SOURCE_MESSAGE,
    INCOME_SALARY_SOURCE_MESSAGE,
    REPORT_INCOMES_TITLE,
)
from categories import CategoriesService, Category
from costs import Cost, CostsService
from finances import Currencies
from incomes import Income, IncomesService
from shared.formatting import get_number_in_frames
from shared.messages import BOLD, INDENTION, ITALIC, LINE_ITEM
from shared.sequences import build_dict_from_sequence
from users import User


class AnalitycsService:
    @classmethod
    def __costs_by_category(cls, costs: list[Cost]):
        attr = "category_id"
        return groupby(sorted(costs, key=attrgetter(attr)), key=attrgetter(attr))

    @classmethod
    def __get_formatted_costs_by_currency_basic(
        cls, categories_by_id: dict[int, Category], costs: Optional[list[Cost]]
    ) -> str:
        text = ""

        if not costs:
            return text

        total_costs_sum: Decimal = sum(costs)  # type: ignore
        sign = "$" if costs[0].currency == Currencies.get_database_value("USD") else ""

        for id, costs_group in cls.__costs_by_category(costs):
            category: Category = categories_by_id[id]
            total_costs: Decimal = sum(costs_group)  # type: ignore
            text += "".join(
                ("\n", LINE_ITEM.format(key=category.name, value=get_number_in_frames((total_costs))), sign)
            )

            percent = (total_costs * Decimal("100") / total_costs_sum).quantize(Decimal("0.1"))
            text += "".join((INDENTION, ITALIC.format(text=f"({percent}%)")))

        text += "".join(
            [
                "\n\n",
                LINE_ITEM.format(
                    key=BOLD.format(text="Total costs"),
                    value=get_number_in_frames(total_costs_sum),
                ),
                sign,
            ]
        )

        return text

    @classmethod
    def __get_formatted_costs_by_currency_detailed(
        cls, categories_by_id: dict[int, Category], costs: Optional[list[Cost]]
    ) -> list[str]:
        report: list[str] = []

        if not costs:
            return report

        sign = "$" if costs[0].currency == Currencies.get_database_value("USD") else ""

        for id, costs_group in cls.__costs_by_category(costs):
            category: Category = categories_by_id[id]
            costs_formatted = ""

            for cost in costs_group:
                cost_date = cost.fdate("%d")
                costs_formatted += "".join(
                    (
                        "\n",
                        INDENTION,
                        LINE_ITEM.format(
                            key=f"{cost_date}  {cost.name}",
                            value=get_number_in_frames(cost.value),
                        ),
                        sign,
                    )
                )

            report.append("\n".join([BOLD.format(text=category.name), costs_formatted, "\n"]))

        return report

    @classmethod
    def __get_detailed_costs(
        cls, categories_by_id: dict[int, Category], costs: Optional[list[Cost]], header: str
    ) -> list[str]:
        """Return costs by category in readable format"""

        results: list[str] = []

        if not costs:
            return results

        rcosts = [el for el in cls.__get_formatted_costs_by_currency_detailed(categories_by_id, costs)]

        if rcosts:
            results.append(ITALIC.format(text=BOLD.format(text=header)))
            results += rcosts

        return results

    @classmethod
    def __get_basic_report(
        cls,
        date: str,
        categories_by_id: dict[int, Category],
        costs: dict[str, list[Cost]],
        incomes: dict[str, list[Income]],
    ) -> str:
        message = BOLD.format(text=date)
        byn_title = CURRENCY_REPORT_TITLE_MESSAGE.format(currency=Currencies.BYN.value)
        usd_title = CURRENCY_REPORT_TITLE_MESSAGE.format(currency=Currencies.USD.value)

        byn_costs_message = cls.__get_formatted_costs_by_currency_basic(
            categories_by_id, costs.get(Currencies.get_database_value("BYN"))
        )
        usd_costs_message = cls.__get_formatted_costs_by_currency_basic(
            categories_by_id, costs.get(Currencies.get_database_value("USD"))
        )

        byn_salary_incomes_message = IncomesService.get_formatted_incomes(
            [i for i in incomes.get(Currencies.get_database_value("BYN"), []) if i.salary], INCOME_SALARY_SOURCE_MESSAGE
        )
        usd_salary_incomes_message = IncomesService.get_formatted_incomes(
            [i for i in incomes.get(Currencies.get_database_value("USD"), []) if i.salary], INCOME_SALARY_SOURCE_MESSAGE
        )
        byn_other_incomes_message = IncomesService.get_formatted_incomes(
            [i for i in incomes.get(Currencies.get_database_value("BYN"), []) if not i.salary],
            INCOME_OTHER_SOURCE_MESSAGE,
        )
        usd_other_incomes_message = IncomesService.get_formatted_incomes(
            [i for i in incomes.get(Currencies.get_database_value("USD"), []) if not i.salary],
            INCOME_OTHER_SOURCE_MESSAGE,
        )

        if byn_costs_message or byn_salary_incomes_message:
            message += "\n".join([byn_title, byn_costs_message, byn_salary_incomes_message, byn_other_incomes_message])

        if usd_costs_message or usd_salary_incomes_message:
            message += "\n".join([usd_title, usd_costs_message, usd_salary_incomes_message, usd_other_incomes_message])

        return message

    @classmethod
    def get_monthly_detailed_report(cls, month: str, category: Optional[Category] = None) -> Iterable[str]:
        """
        This is a general interface to get monthly costs and incomes analytics
        Return the list of costs by category with headers.
        The last element in the list is incomes
        """

        costs: dict[str, list[Cost]] = CostsService.get_monthly_costs(month, category)
        incomes: dict[str, list[Income]] = IncomesService.get_monthly_incomes(month)
        categories_by_id: dict[int, Category] = build_dict_from_sequence(
            CategoriesService.CACHED_CATEGORIES,
            "id",
        )  # type: ignore

        report = [
            *cls.__get_detailed_costs(
                categories_by_id, costs.get(Currencies.get_database_value("BYN")), Currencies.BYN.value
            ),
            *cls.__get_detailed_costs(
                categories_by_id, costs.get(Currencies.get_database_value("USD")), Currencies.USD.value
            ),
        ]

        if not category:
            cached_users: dict[int, User] = {}
            byn_incomes: str = IncomesService.get_detailed_incomes_message(
                cached_users, incomes.get(Currencies.get_database_value("BYN"))
            )
            usd_incomes: str = IncomesService.get_detailed_incomes_message(
                cached_users, incomes.get(Currencies.get_database_value("USD"))
            )

            incomes_message = "\n".join(
                ["".join((BOLD.format(text=REPORT_INCOMES_TITLE), "\n")), byn_incomes, usd_incomes]
            )
            report.append(incomes_message)

        return report

    @classmethod
    def get_monthly_basic_report(cls, month: str) -> Iterable[str]:
        costs: dict[str, list[Cost]] = CostsService.get_monthly_costs(month)
        incomes: dict[str, list[Income]] = IncomesService.get_monthly_incomes(month)
        categories_by_id: dict[int, Category] = build_dict_from_sequence(
            CategoriesService.CACHED_CATEGORIES,
            "id",
        )  # type: ignore

        report = cls.__get_basic_report(month, categories_by_id, costs, incomes)

        return [report]

    @classmethod
    def get_annyally_report(cls, year: str) -> str:
        """Get annually report. Costs by category. All incomes"""

        costs: dict[str, list[Cost]] = CostsService.get_annually_costs(year)
        incomes: dict[str, list[Income]] = IncomesService.get_annually_incomes(year)
        categories_by_id: dict[int, Category] = build_dict_from_sequence(
            CategoriesService.CACHED_CATEGORIES,
            "id",
        )  # type: ignore

        report = cls.__get_basic_report(year, categories_by_id, costs, incomes)

        return report
